from __future__ import absolute_import, division, print_function, unicode_literals

import sys
import argparse

from gratipay import wireup
from gratipay.sync_npm.sync import serialize, upsert
from gratipay.sync_npm import readmes as _readmes


def parse_args(argv):
    p = argparse.ArgumentParser()
    p.add_argument('command', choices=['serialize', 'upsert', 'fetch-readmes', 'process-readmes'])
    p.add_argument('path', help='the path to the input file', nargs='?', default='/dev/stdin')
    return p.parse_args(argv)


subcommands = { 'serialize': serialize
              , 'upsert': upsert
              , 'fetch-readmes': lambda env, args, db: _readmes.fetch(db)
              , 'process-readmes': lambda env, args, db: _readmes.process(db)
               }


def main(argv=sys.argv):
    env = wireup.env()
    args = parse_args(argv[1:])
    db = wireup.db(env)
    subcommands[args.command.replace('-', '_')](env, args, db)
