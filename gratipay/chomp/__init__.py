"""Process npm artifacts.

The main function is exposed as a console script named `chomp` via setup.py.

"""
from __future__ import absolute_import, division, print_function, unicode_literals
from collections import OrderedDict

import argparse
import sys

import psycopg2

import requests

from gratipay.utils import markdown
from io import StringIO

class NPM(object):
    """Represent npm.
    """
    def __init__(self):
        self.name = 'npm'

    def parse(self, package, package_manager_id, package_id):
        """Given an npm package dict, return a dict of info and a list of emails to be imported.
        """
        out = OrderedDict()
        out['id'] = str(package_id)
        out['package_manager_id'] = str(package_manager_id)
        out['name'] = package['name']
        out['description'] = package['description'] if 'description' in package else ''
        if 'time' in package:
            if type(package['time']) is dict and 'modified' in package['time']:
                out['mtime'] = package['time']['modified']
        else:
            out['mtime'] = 'now()'

        emails = []
        for key in ('authors', 'maintainers'):
            for person in package.get(key, []):
                if type(person) is dict:
                    email = person.get('email')
                    if email:
                        emails.append(OrderedDict([
                            ('package_id', str(package_id)),
                            ('email', email)
                        ]))

        return out, emails

    def fetch_catalog(self):
        r = requests.get('https://registry.npmjs.com/-/all', verify=False)
        r.raise_for_status()
        return r.json()


def stringify(obj):
    return '\t'.join([v for k, v in obj.iteritems()])

def insert_catalog_for(pm):
    catalog = pm.fetch_catalog()
    conn = psycopg2.connect(host='localhost', database='gratipay')
    if catalog:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO package_managers (name)
                VALUES (%s) RETURNING id
            """, (pm.name,))
        package_manager_id = cursor.fetchone()[0]
        package_id = 0 # Mass assign ids so they are usable during email insertion
        package_data = StringIO()
        email_data = StringIO()
        for k, v in catalog.iteritems():
            package_id += 1
            package, emails = pm.parse(v, package_manager_id, package_id)
            package_data.write(stringify(package) + '\n')
            for email in emails:
                email_data.write(stringify(email) + '\n')
        package_data.seek(0)
        email_data.seek(0)

        cursor.copy_from(package_data, 'packages', columns=["id", "package_manager_id", "name", "description"])
        cursor.copy_from(email_data, 'package_emails', columns=["package_id", "email"])
    conn.commit()

def update_database(SQL):
    pass


def parse_args(argv):
    p = argparse.ArgumentParser()
    p.add_argument( 'if_modified_since'
                  , help='a number of minutes in the past, past which we need new updates'
                   )
    p.add_argument('package_manager'
                  , help='the name of the package manager to import from'
                   )
    return p.parse_args(argv)


def main(argv=sys.argv):
    pm_arg = parse_args(argv[1:]).package_manager
    if pm_arg == 'npm':
        pm = NPM()
    insert_catalog_for(pm)
