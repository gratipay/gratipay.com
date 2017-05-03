# -*- coding: utf-8 -*-
"""Define the top-level function for the ``sync-npm`` cli.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import time

from aspen import log
from couchdb import Database

from gratipay import wireup
from gratipay.utils import sentry


def get_last_seq(db):
    return db.one('SELECT npm_last_seq FROM worker_coordination')


def production_change_stream(seq):
    """Given a sequence number in the npm registry change stream, start
    streaming from there!
    """
    npm = Database('https://skimdb.npmjs.com/registry')
    return npm.changes(feed='continuous', include_docs=True, since=seq)


def process_doc(doc):
    """Return a smoothed-out doc, or None if it's not a package doc, meaning
    there's no name key and it's probably a design doc, per:

        https://github.com/npm/registry/blob/aef8a275/docs/follower.md#clean-up

    """
    if 'name' not in doc:
        return None
    name = doc['name']
    description = doc.get('description', '')
    emails = [e for e in [m.get('email') for m in doc.get('maintainers', [])] if e.strip()]
    return {'name': name, 'description': description, 'emails': sorted(set(emails))}


def consume_change_stream(change_stream, db):
    """Given a function similar to :py:func:`production_change_stream` and a
    :py:class:`~GratipayDB`, read from the stream and write to the db.

    The npm registry is a CouchDB app, which means we get a change stream from
    it that allows us to follow registry updates in near-realtime. Our strategy
    here is to maintain open connections to both the registry and our own
    database, and write as we read.

    """
    last_seq = get_last_seq(db)
    log("Picking up with npm sync at {}.".format(last_seq))
    with db.get_connection() as conn:
        for change in change_stream(last_seq):
            processed = process_doc(change['doc'])
            if not processed:
                continue
            cursor = conn.cursor()
            cursor.run('''
            INSERT INTO packages
                        (package_manager, name, description, emails)
                 VALUES ('npm', %(name)s, %(description)s, %(emails)s)

            ON CONFLICT (package_manager, name) DO UPDATE
                    SET description=%(description)s, emails=%(emails)s
            ''', processed)
            cursor.run('UPDATE worker_coordination SET npm_last_seq=%s', (change['seq'],))
            cursor.connection.commit()


def main():
    """This function is installed via an entrypoint in ``setup.py`` as
    ``sync-npm``.

    Usage::

      sync-npm

    """
    env = wireup.env()
    db = wireup.db(env)
    while 1:
        with sentry.teller(env):
            consume_change_stream(production_change_stream, db)
        try:
            last_seq = get_last_seq(db)
            sleep_for = 60
            log( 'Encountered an error, will pick up with %s in %s seconds (Ctrl-C to exit) ...'
               % (last_seq, sleep_for)
                )
            time.sleep(sleep_for)  # avoid a busy loop if thrashing
        except KeyboardInterrupt:
            return
