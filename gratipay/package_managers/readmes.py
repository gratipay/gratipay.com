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


def Syncer(db):
    def sync(dirty, fetch=http_fetch):
        """Update all info for one package.
        """
        log(dirty.name)
        full = fetch(dirty.name)

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
               SET readme=%s
                 , readme_raw=%s
                 , readme_type=%s
             WHERE package_manager=%s
               AND name=%s

        ''', ( markdown.marky(full['readme'])
             , full['readme']
             , 'x-markdown/npm'
             , dirty.package_manager
             , dirty.name
              ))

    return sync


def sync_all(db):
    dirty = db.all('SELECT package_manager, name FROM packages WHERE readme_raw IS NULL '
                   'ORDER BY package_manager DESC, name DESC')
    threaded_map(Syncer(db), dirty, 4)
