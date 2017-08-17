# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import requests
from couchdb import Database

from gratipay.models.package import NPM, Package


REGISTRY_URL = 'https://replicate.npmjs.com/'


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


def consume_change_stream(stream, db):
    """Given an iterable of CouchDB change notifications and a
    :py:class:`~GratipayDB`, read from the stream and write to the db.

    The npm registry is a CouchDB app, which means we get a change stream from
    it that allows us to follow registry updates in near-realtime. Our strategy
    here is to maintain open connections to both the registry and our own
    database, and write as we read.

    """
    with db.get_connection() as connection:
        for change in stream:

            # Decide what to do.
            if change.get('deleted'):
                package = Package.from_names(NPM, change['id'])
                if not package:
                    # As a result of CouchDB's compaction algorithm, we might
                    # receive 'deleted' events for docs even if we haven't seen
                    # the corresponding events for when the doc was created
                    continue
                op, kw = package.delete, {}
            else:
                op = Package.upsert
                doc = change.get('doc')
                if not doc:
                    continue    # We've seen this in the wild.
                kw = process_doc(doc)
                if not kw:
                    continue
                kw['package_manager'] = NPM

            # Do it.
            cursor = connection.cursor()
            kw['cursor'] = cursor
            op(**kw)
            cursor.run('UPDATE worker_coordination SET npm_last_seq=%(seq)s', change)
            connection.commit()


def check(db, _print=print):
    ours = db.one('SELECT npm_last_seq FROM worker_coordination')
    theirs = int(requests.get(REGISTRY_URL).json()['update_seq'])
    _print("count#npm-sync-lag={}".format(theirs - ours))
