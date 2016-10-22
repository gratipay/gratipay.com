"""Process npm artifacts.

The main function is exposed as a console script named `chomp` via setup.py.

"""
from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import sys

import requests
from gratipay.utils import markdown


def from_npm(package):
    """Given an npm package dict, return a dict of info and a list of emails.
    """
    out= {}
    out['name'] = package['name']
    out['description'] = package['description']
    out['long_description'] = markdown.marky(package['readme'])
    out['long_description_raw'] = package['readme']
    out['long_description_type'] = 'x-text/marky-markdown'

    emails = []
    for key in ('authors', 'maintainers'):
        for person in package.get(key, []):
            if type(person) is dict:
                email = person.get('email')
                if email:
                    emails.append(email)

    return out, emails


def process_catalog(catalog):
    SQL = ''
    return SQL


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
    process_catalog(fetch_catalog(), ims)
