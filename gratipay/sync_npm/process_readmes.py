# -*- coding: utf-8 -*-
"""Subcommand for processing readmes.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

from . import log
from ..utils import markdown
from ..utils.threaded_map import threaded_map


def Processor(db, _render):
    def process(dirty):
        """Processes the readme for a single package.
        """
        log('processing', dirty.name)
        package = db.one( 'SELECT readme_raw, name, description FROM packages '
                          'WHERE package_manager=%s and name=%s and readme_needs_to_be_processed'
                        , (dirty.package_manager, dirty.name)
                        , back_as=dict
                         )
        if package is None:
            return
        processed = _render(package.pop('readme_raw'), package=package)
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


def main(env, args, db, sentrified, _render=markdown.render_like_npm):
    """For all packages where ``readme_needs_to_be_processed`` is ``true``, run
    ``readme_raw`` through ``marky-markdown`` and store the result in
    ``readme``. Reset ``readme_needs_to_be_processed`` to ``false``. This runs
    in four threads.

    """
    dirty = db.all('SELECT package_manager, name '
                   'FROM packages WHERE readme_needs_to_be_processed '
                   'ORDER BY package_manager DESC, name DESC')
    threaded_map(sentrified(Processor(db, _render)), dirty, 4)
