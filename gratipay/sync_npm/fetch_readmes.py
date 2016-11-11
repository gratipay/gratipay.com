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
    try:
        r = requests.get('https://registry.npmjs.com/' + package_name)
    except requests.ConnectionError:
        return (600, None)  # will be skipped and retried later
    if r.status_code in (200, 404):
        out = r.json()
    else:
        out = None
    return r.status_code, out


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

        if code == 404:
            log(dirty.name, 'is {}; deleting'.format(code))
            delete_package(db, dirty, clean)
            return

        if code != 200:
            assert clean is None
            log(dirty.name, 'is {}; skipping'.format(code))
            return

        assert dirty.name == clean['name']

        if 'readme' not in clean:
            log(clean['name'], 'has no readme; adding an empty one')
            clean['readme'] = ''
        elif type(clean['readme']) is not unicode:
            log(clean['name'], 'has a readme of type {} instead of unicode; '
                               'replacing with an empty one'
                               .format(type(clean['readme'])))
            clean['readme'] = ''

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
