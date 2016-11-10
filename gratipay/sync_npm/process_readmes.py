# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals
"""Subcommand for processing readmes.
"""

from . import log
from ..utils import markdown
from ..utils.threaded_map import threaded_map


def Processor(db):
    def process(dirty):
        """Processes the readme for a single package.
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


def main(env, args, db):
    dirty = db.all('SELECT package_manager, name '
                   'FROM packages WHERE readme_needs_to_be_processed '
                   'ORDER BY package_manager DESC, name DESC')
    threaded_map(Processor(db), dirty, 4)
