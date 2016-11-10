# -*- coding: utf-8 -*-
"""Subcommand for fetching readmes.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import requests

from . import log
from ..utils.threaded_map import threaded_map


def fetch_from_public_registry(package_name):
    """Fetch a package from the public npm registry.
    """
    r = requests.get('https://registry.npmjs.com/' + package_name)
    if r.status_code not in (200, 404):
        log(r.status_code, 'for', package_name)
        return None
    return r.status_code, r.json()


def delete_package(db, dirty, clean):
    db.run( 'DELETE FROM packages WHERE package_manager=%s AND name=%s'
          , (dirty.package_manager, dirty.name)
           )


def update_package(db, dirty, clean):
    db.run('''

        UPDATE packages
           SET readme_needs_to_be_processed=true
             , readme_raw=%s
             , readme_type=%s
         WHERE package_manager=%s
           AND name=%s

    ''', ( clean['readme']
         , 'x-markdown/marky'
         , dirty.package_manager
         , dirty.name
          ))


def Fetcher(db, _fetch):
    def fetch(dirty):
        """Update all info for one package.
        """
        log('fetching', dirty.name)
        code, clean = _fetch(dirty.name)

        assert code in (200, 404)
        if code == 404:
            log(dirty.name, 'is 404; deleting')
            delete_package(db, dirty, clean)
        elif clean['name'] != dirty.name:
            log('expected', dirty.name, 'got', clean['name'])
        elif 'readme' not in clean:
            log('no readme in', clean['name'])
        elif clean:
            update_package(db, dirty, clean)

    return fetch


def main(env, args, db, sentrified, _fetch=fetch_from_public_registry):
    """Populate ``readme_raw`` for all packages where ``readme_raw`` is null.
    The ``readme_type`` is set to ``x-markdown/marky``, and
    ``readme_needs_to_be_processed`` is set to ``true``. If the fetched package
    is missing or malformed, we log the condition and continue. This runs in
    four threads.

    """
    dirty = db.all('SELECT package_manager, name '
                   'FROM packages WHERE readme_raw IS NULL '
                   'ORDER BY package_manager DESC, name DESC')
    threaded_map(sentrified(Fetcher(db, _fetch)), dirty, 4)
