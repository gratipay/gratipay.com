"""Process package artifacts.

The main function is exposed as a console script named `chomp` via setup.py.

"""
from __future__ import absolute_import, division, print_function, unicode_literals
from collections import OrderedDict
from io import StringIO
from gratipay.utils import markdown

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
        out['package_manager_id'] = str(self.id)
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
        # import json
        # return json.loads('{"a11y-announcer":{"name":"a11y-announcer","description":"An accessible ember route change announcer","dist-tags":{"latest":"1.0.2"},"maintainers":[{"name":"robdel12","email":"Robertdeluca19@gmail.com"}],"homepage":"https://github.com/ember-a11y/a11y-announcer#readme","keywords":["ember-addon","ember accessibility","ember router","a11y-announcer"],"repository":{"type":"git","url":"git+https://github.com/ember-a11y/a11y-announcer.git"},"author":{"name":"Robert DeLuca"},"bugs":{"url":"https://github.com/ember-a11y/a11y-announcer/issues"},"license":"MIT","readmeFilename":"README.md","users":{"jalcine":true,"unwiredbrain":true},"time":{"modified":"2016-08-13T23:03:37.135Z"},"versions":{"1.0.2":"latest"}}}')
        r = requests.get('https://registry.npmjs.com/-/all', verify=False)
        r.raise_for_status()
        return r.json()


def stringify(obj):
    return '\t'.join([v for k, v in obj.iteritems()]) + '\n'

def insert_package_manager(pm, cursor):
    """Insert a new package manager returning it's id.
    """
    cursor.execute("""
        INSERT INTO package_managers (name)
            VALUES (%s) RETURNING id
        """, (pm.name,))
    return cursor.fetchone()[0]

def package_manager_exists(pm, cursor):
    cursor.execute("""
        SELECT package_managers.id
          FROM package_managers
         WHERE package_managers.name = (%s)
        """, (pm.name,))
    return cursor.fetchone()

def insert_catalog_for(pm, cursor):
    """Insert all packages for a given package manager.
    """
    catalog = pm.fetch_catalog()
    if catalog:
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

        cursor.copy_from(package_stream, 'packages', columns=["id", "package_manager_id", "name", "description", "mtime"])
        cursor.copy_from(email_stream, 'package_emails', columns=["package_id", "email"])

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

    conn = psycopg2.connect(host='localhost', database='gratipay')
    cursor = conn.cursor()

    if package_manager_exists(pm, cursor):
        print("This package manager already exists!")
    else:
        package_manager_id = insert_package_manager(pm, cursor)
        setattr(pm, 'id', package_manager_id)
        insert_catalog_for(pm, cursor)

    conn.commit()
