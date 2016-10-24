"""Process package artifacts.

The main function is exposed as a console script named `chomp` via setup.py.

"""
from __future__ import absolute_import, division, print_function, unicode_literals
from collections import OrderedDict
from io import StringIO

import argparse
import sys
import psycopg2
import requests


class NPM(object):
    """Represent npm.
    """
    def __init__(self):
        self.name = 'npm'

    def parse(self, package, package_id):
        """Given an npm package dict, return a dict of info and a list of emails to be imported.
        """
        out = OrderedDict()
        out['id'] = str(package_id)
        out['package_manager'] = self.name
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
    # XXX What if there is a `\t` in `v`?
    return '\t'.join([v for k, v in obj.iteritems()]) + '\n'

def package_manager_exists(pm, cursor):
    cursor.execute("""
        SELECT package_managers.id
          FROM package_managers
         WHERE package_managers.name = (%s)
        """, (pm.name,))
    return cursor.fetchone()

def extract_info_from_catalog(pm, catalog):
    """Extract info from the catalog for the given package manager.
    """
    package_id = 0 # Mass assign ids so they are usable during email insertion
    package_stream, email_stream = StringIO(), StringIO()
    for k, v in catalog.iteritems():
        if type(v) is dict:
            package_id += 1
            package, emails = pm.parse(v, package_id)
            package_stream.write(stringify(package))
            for email in emails:
                email_stream.write(stringify(email))
    package_stream.seek(0)
    email_stream.seek(0)
    return package_stream, email_stream

def copy_into_db(cursor, package_stream, email_stream):
    cursor.copy_from(package_stream, 'packages',
                     columns=["id", "package_manager", "name", "description", "mtime"])
    cursor.copy_from(email_stream, 'package_emails', columns=["package_id", "email"])

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

    conn = psycopg2.connect(host='localhost', database='gratipay')
    cursor = conn.cursor()

    if package_manager_exists(pm, cursor):
        print("This package manager already exists!")
    else:
        catalog = pm.fetch_catalog()
        packages, emails = extract_info_from_catalog(catalog)
        copy_into_db(cursor, packages, emails)

    conn.commit()
