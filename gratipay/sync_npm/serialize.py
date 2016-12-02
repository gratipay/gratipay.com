# -*- coding: utf-8 -*-
"""Subcommand for serializing JSON from npm into CSV.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import csv
import sys
import time

from . import log, sentry


def import_ijson(env):
    if env.require_yajl:
        import ijson.backends.yajl2_cffi as ijson
    else:
        import ijson
    return ijson


def arrayize(seq):
    """Given a sequence of ``str``, return a Postgres array literal ``str``.
    This is scary and I wish ``psycopg2`` had something we could use.

    """
    array = []
    for item in seq:
        assert type(item) is str
        escaped = item.replace(b'\\', b'\\\\').replace(b'"', b'\\"')
        quoted = b'"' + escaped + b'"'
        array.append(quoted)
    joined = b', '.join(array)
    return b'{' + joined + b'}'


def serialize_one(out, package):
    """Take a single package ``dict`` and emit a CSV serialization suitable for
    Postgres COPY.

    """
    if not package or package['name'].startswith('_'):
        log('skipping', package)
        return 0

    row = ( package['package_manager']
          , package['name']
          , package['description']
          , arrayize(package['emails'])
           )

    out.writerow(row)
    return 1


def serialize(env, args, db):
    ijson = import_ijson(env)

    path = args.path
    parser = ijson.parse(open(path))
    start = time.time()
    package = None
    nprocessed = 0
    out = csv.writer(sys.stdout)

    def log_stats():
        log("processed {} packages in {:3.0f} seconds"
            .format(nprocessed, time.time() - start))

    for prefix, event, value in parser:

        if not prefix and event == b'map_key':

            # Flush the current package. We count on the first package being garbage.
            processed = serialize_one(out, package)
            nprocessed += processed
            if processed and not(nprocessed % 1000):
                log_stats()

            # Start a new package.
            package = { 'package_manager': b'npm'
                      , 'name': value
                      , 'description': b''
                      , 'emails': []
                       }

        key = lambda k: package['name'] + b'.' + k

        if event == b'string':
            assert type(value) is unicode  # Who knew? Seems to decode only for `string`.
            value = value.encode('utf8')
            if prefix == key(b'description'):
                package['description'] = value
            elif prefix in (key(b'author.email'), key(b'maintainers.item.email')):
                package['emails'].append(value)

    nprocessed += serialize_one(out, package)  # Don't forget the last one!
    log_stats()


def main(env, args, db):
    """Consume raw JSON from the npm registry via ``args.path``, and spit out
    CSV for Postgres to stdout. Uses ``ijson``, requiring the ``yajl_cffi``
    backend if ``env.require_yajl`` is ``True``.

    """
    with sentry(env):
        serialize(env, args, db)
