# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import requests
from aspen import log
from couchdb import Database


REGISTRY_URL = 'https://skimdb.npmjs.com/registry'


def get_last_seq(db):
    return db.one('SELECT npm_last_seq FROM worker_coordination')


def production_change_stream(seq):
    """Given a sequence number in the npm registry change stream, start
    streaming from there!
    """
    return Database(REGISTRY_URL).changes(feed='continuous', include_docs=True, since=seq)


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
    with db.get_connection() as connection:
        for change in change_stream(last_seq):
            if change.get('deleted'):
                # Hack to work around conflation of design docs and packages in updates
                op, doc = delete, {'name': change['id']}
            else:
                op, doc = upsert, change['doc']
            processed = process_doc(doc)
            if not processed:
                continue
            cursor = connection.cursor()
            op(cursor, processed)
            cursor.run('UPDATE worker_coordination SET npm_last_seq=%(seq)s', change)
            connection.commit()


def delete(cursor, processed):
    cursor.run("DELETE FROM packages WHERE package_manager='npm' AND name=%(name)s", processed)


def upsert(cursor, processed):
    cursor.run('''
    INSERT INTO packages
                (package_manager, name, description, emails)
         VALUES ('npm', %(name)s, %(description)s, %(emails)s)

    ON CONFLICT (package_manager, name) DO UPDATE
            SET description=%(description)s, emails=%(emails)s
    ''', processed)


def check(db, _print=print):
    ours = db.one('SELECT npm_last_seq FROM worker_coordination')
    theirs = int(requests.get(REGISTRY_URL).json()['update_seq'])
    _print("count#npm-sync-lag={}".format(theirs - ours))
