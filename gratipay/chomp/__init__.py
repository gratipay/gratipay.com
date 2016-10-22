"""Process npm artifacts.

The main function is exposed as a console script named `chomp` via setup.py.

"""
from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import sys

import psycopg2

import requests

from gratipay.utils import markdown
from io import StringIO

def from_npm(package, package_id):
    """Given an npm package dict, return a dict of info and a list of emails.
    """
    out = {}
    out['id'] = str(package_id)
    out['name'] = package['name']
    out['description'] = package['description']
    out['package_manager_id'] = "1" # Todo - generalize
    out['long_description'] = 'null'
    out['long_description_raw'] = 'null'
    out['long_description_type'] = 'null'

    emails = []
    for key in ('authors', 'maintainers'):
        for person in package.get(key, []):
            if type(person) is dict:
                email = person.get('email')
                if email:
                    emails.append({ 'package_id': str(package_id), 'email': email })

    return out, emails

def stringify(obj):
    return '\t'.join([v for k, v in obj.iteritems()])

def insert_catalog(catalog):
    package_id = 0
    package_data = StringIO()
    email_data = StringIO()
    for k, v in catalog.iteritems():
        package_id += 1
        package, emails = from_npm(v, package_id)
        package_data.write(stringify(package) + '\n')
        for email in emails:
            email_data.write(stringify(email) + '\n')


def fetch_catalog():
    # r = requests.get('https://registry.npmjs.com/-/all', verify=False)
    # r.raise_for_status()
    # return r.json()
    import json
    return json.loads('{"a11y-announcer":{"name":"a11y-announcer","description":"An accessible ember route change announcer","dist-tags":{"latest":"1.0.2"},"maintainers":[{"name":"robdel12","email":"Robertdeluca19@gmail.com"}],"homepage":"https://github.com/ember-a11y/a11y-announcer#readme","keywords":["ember-addon","ember accessibility","ember router","a11y-announcer"],"repository":{"type":"git","url":"git+https://github.com/ember-a11y/a11y-announcer.git"},"author":{"name":"Robert DeLuca"},"bugs":{"url":"https://github.com/ember-a11y/a11y-announcer/issues"},"license":"MIT","readmeFilename":"README.md","users":{"jalcine":true,"unwiredbrain":true},"time":{"modified":"2016-08-13T23:03:37.135Z"},"versions":{"1.0.2":"latest"}}}')


def update_database(SQL):
    pass


def parse_args(argv):
    p = argparse.ArgumentParser()
    p.add_argument( 'if_modified_since'
                  , help='a number of minutes in the past, past which we need new updates'
                   )
    return p.parse_args(argv)


def main(argv=sys.argv):
    ims = parse_args(argv[1:]).if_modified_since
    insert_catalog(fetch_catalog())
