from __future__ import absolute_import, division, print_function, unicode_literals

import sys

import requests

from gratipay.utils import markdown
from gratipay.utils.threaded_map import threaded_map
from threading import Lock


log_lock = Lock()

def log(*a, **kw):
    with log_lock:
        print(*a, file=sys.stderr, **kw)


def http_fetch(package_name):
    r = requests.get('https://registry.npmjs.com/' + package_name)
    if r.status_code != 200:
        log(r.status_code, 'for', package_name)
        return None
    return r.json()


def Fetcher(db, _fetch=http_fetch):
    def fetch(dirty):
        """Update all info for one package.
        """
        log(dirty.name)
        full = _fetch(dirty.name)

        if not full:
            return
        elif full['name'] != dirty.name:
            log('expected', dirty.name, 'got', full['name'])
            return
        elif 'readme' not in full:
            log('no readme in', full['name'])
            return

        db.run('''

            UPDATE packages
               SET readme_needs_to_be_processed=true
                 , readme_raw=%s
                 , readme_type=%s
             WHERE package_manager=%s
               AND name=%s

        ''', ( full['readme']
             , 'x-markdown/marky'
             , dirty.package_manager
             , dirty.name
              ))

    return fetch


def Processor(db):
    def process(dirty):
        """Processes the readme for a single page.
        """
        log(dirty.name)
        raw = db.one( 'SELECT readme_raw FROM packages '
                      'WHERE package_manager=%s and name=%s and readme_needs_to_be_processed'
                    , (dirty.package_manager, dirty.name)
                     )
        if raw is None:
            return
        processed = markdown.render_like_npm(raw)
        db.run('''

            UPDATE packages
               SET readme=%s
                 , readme_needs_to_be_processed=false
             WHERE package_manager=%s
               AND name=%s

        ''', ( processed
             , dirty.package_manager
             , dirty.name
              ))

    return process


def fetch(db, _fetch=http_fetch):
    dirty = db.all('SELECT package_manager, name '
                   'FROM packages WHERE readme_raw IS NULL '
                   'ORDER BY package_manager DESC, name DESC')
    threaded_map(Fetcher(db, _fetch), dirty, 4)


def process(db):
    dirty = db.all('SELECT id, package_manager, name, description, readme_raw '
                   'FROM packages WHERE readme_needs_to_be_processed '
                   'ORDER BY package_manager DESC, name DESC')
    threaded_map(Processor(db), dirty, 4)

