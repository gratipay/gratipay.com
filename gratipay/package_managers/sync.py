"""Sync our database with package managers. Just npm for now.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import csv
import sys
import time
import uuid

from gratipay.package_managers import readmes as _readmes


log = lambda *a: print(*a, file=sys.stderr)
NULL = uuid.uuid4().hex


def import_ijson():
    import ijson.backends.yajl2_cffi as ijson
    return ijson


def arrayize(seq):
    """Given a sequence of str, return a Postgres array literal str.
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
    """Takes a package and emits a serialization suitable for COPY.
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


def serialize(args):
    """Consume raw JSON from the npm registry and spit out CSV for Postgres.
    """
    ijson = import_ijson()

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


def upsert(args):
    from gratipay import wireup
    db = wireup.db(wireup.env())
    fp = open(args.path)
    with db.get_cursor() as cursor:
        assert cursor.connection.encoding == 'UTF8'

        # http://tapoueh.org/blog/2013/03/15-batch-update.html
        cursor.run("CREATE TEMP TABLE updates (LIKE packages INCLUDING ALL) ON COMMIT DROP")
        cursor.copy_expert('COPY updates (package_manager, name, description, emails) '
                           "FROM STDIN WITH (FORMAT csv, NULL '%s')" % NULL, fp)
        cursor.run("""

            WITH updated AS (
                UPDATE packages p
                   SET package_manager = u.package_manager
                     , description = u.description
                     , emails = u.emails
                  FROM updates u
                 WHERE p.name = u.name
             RETURNING p.name
            )
            INSERT INTO packages(package_manager, name, description, emails)
                 SELECT package_manager, name, description, emails
                   FROM updates u LEFT JOIN updated USING(name)
                  WHERE updated.name IS NULL
               GROUP BY u.package_manager, u.name, u.description, u.emails

        """)


def readmes(args):
    from gratipay import wireup
    db = wireup.db(wireup.env())
    _readmes.sync_all(db)


def parse_args(argv):
    p = argparse.ArgumentParser()
    p.add_argument('command', choices=['serialize', 'upsert', 'readmes'])
    p.add_argument('path', help='the path to the input file', nargs='?', default='/dev/stdin')
    return p.parse_args(argv)


def main(argv=sys.argv):
    args = parse_args(argv[1:])
    globals()[args.command](args)
