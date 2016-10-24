#!/usr/bin/env python
from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import sys
import time
from collections import OrderedDict
from psycopg2.extensions import adapt

import ijson.backends.yajl2_cffi as ijson


log = lambda *a: print(*a, file=sys.stderr)


def serialize_one(package):
    """Takes a package and returns a serialization suitable for COPY.
    """
    if not package or package['name'].startswith('_'):
        log('skipping', package)
        return 0

    out = []
    for k,v in package.iteritems():
        if type(v) is unicode:
            v = v.replace('\n', r'\n')
            v = v.replace('\r', r'\r')
            v = v.encode('utf8')
        out.append(adapt(v).getquoted())
        if type(v) is list:
            # Gah. I am a dog. I have no idea what I'm doing. O.O
            stripped = out[-1][len('ARRAY['):-1]
            out[-1] = b'{' + stripped  + b'}'
    print(b'\t'.join(out))
    return 1


def serialize(args):
    """
    """
    path = args.path
    parser = ijson.parse(open(path))
    start = time.time()
    package = None
    nprocessed = 0

    def log_stats():
        log("processed {} packages in {:3.0f} seconds"
            .format(nprocessed, time.time() - start))

    for prefix, event, value in parser:

        prefix = prefix.decode('utf8')
        if type(value) is str:
            value = value.decode('utf8')

        if not prefix and event == 'map_key':

            # Flush the current package. We count on the first package being garbage.
            processed = serialize_one(package)
            nprocessed += processed
            if processed and not(nprocessed % 1000):
                log_stats()

            if nprocessed == 5555:
                break  # XXX

            # Start a new package.
            package = OrderedDict([ ('package_manager', 'npm')
                                  , ('name', value)
                                  , ('description', '')
                                  , ('emails', [])
                                   ])

        key = lambda k: package['name'] + '.' + k

        if event == 'string':
            if prefix == key('description'):
                package['description'] = value
            elif prefix in (key('author.item.email'), key('maintainers.item.email')):
                package['emails'].append(value)

    log_stats()


def upsert(args):
    from gratipay import wireup
    db = wireup.db(wireup.env())
    fp = open(args.path)
    with db.get_cursor() as cursor:
        cursor.run("CREATE TEMP TABLE updates (LIKE packages INCLUDING ALL) ON COMMIT DROP")
        cursor.copy_from( fp
                        , 'updates'
                        , columns=['package_manager', 'name', 'description', 'emails']
                         )
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



def parse_args(argv):
    p = argparse.ArgumentParser()
    p.add_argument('command', choices=['serialize', 'upsert'])
    p.add_argument('path', help="the path to the input file")
    p.add_argument( '-i', '--if_modified_since'
                  , help='a number of minutes in the past, past which we would like to see new '
                         'updates (only meaningful for `serialize`; -1 means all!)'
                  , type=int
                  , default=-1
                   )
    return p.parse_args(argv)


def main(argv=sys.argv):
    args = parse_args(argv[1:])
    globals()[args.command](args)


if __name__ == '__main__':
    main()
