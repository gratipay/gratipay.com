# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import re
import json
import bleach
import requests
from gratipay.utils import markdown

REGISTRY_URL = 'https://www.npmjs.com/packages/'


def get_dirty_packages(db):
    return db.run('SELECT name FROM packages WHERE description_dirty=true;')


def get_npm_decription(pkg):
    """Given a package name return the raw ld+json desciption from npmjs.com
    """
    raw_html = requests.get("https://www.npmjs.com/package/Express")
    raw_json = re.match( r'.*?<script type="application/ld\+json">(.*?)</script>.*'
                            , raw_html.text
                            , re.MULTILINE | re.DOTALL
                        ).groups()[0]
    return json.loads(raw_json)['description']


def scrub_description(raw_desc):
    """Return a bleached description of a package description
    """
    if not raw_desc:
        return None
    raw_markup = markdown.render_and_scrub(raw_desc).unescape()
    if '=' in raw_markup:
        raw_markup = raw_markup.strip('=')
    return bleach.clean(raw_markup, tags=[''],strip=True)


def clean_packages(stream, db):
    """Check the Gratipay database and retireve the list of packages that need to be
       cleaned. This is done by selecting the package name whose description_dirty
       field is set to true. For each of the packages names returned retieve the
       npmjs.com package page and using regex extract the ld+json description. The
       description that is retrieve is then cleaned using bleach and inserted into
       description_rendered for that package.
    """
    dirty_packages = get_dirty_packages(db)
    with db.get_connection() as connection:
        for name in dirty_packages:

            op = Package.update_description_rendered
            raw_desc = get_npm_description(name)
            clean_desc = scrub_description(raw_desc)
            if not clean_desc:
                continue
            kw = {'name' = name, 'description_rendered': clean_desc }
            kw['package_manager'] = 'npm'

            # Do it.
            cursor = connection.cursor()
            kw['cursor'] = cursor
            op(**kw)
            connection.commit()


