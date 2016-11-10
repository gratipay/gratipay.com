# -*- coding: utf-8 -*-
"""Define the top-level function for the ``sync-npm`` cli.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import sys
import argparse

from gratipay import wireup
from gratipay.sync_npm import serialize, upsert, fetch_readmes, process_readmes


def parse_args(argv):
    p = argparse.ArgumentParser()
    p.add_argument('command', choices=['serialize', 'upsert', 'fetch-readmes', 'process-readmes'])
    p.add_argument('path', help='the path to the input file', nargs='?', default='/dev/stdin')
    return p.parse_args(argv)


subcommands = { 'serialize': serialize.main
              , 'upsert': upsert.main
              , 'fetch-readmes': fetch_readmes.main
              , 'process-readmes': process_readmes.main
               }


def main(argv=sys.argv):
    """This function is installed via an entrypoint in ``setup.py`` as ``sync-npm``.

    Usage::

      sync-npm {serialize,upsert,fetch-readmes,process-readmes} {<filepath>}

    ``<filepath>`` defaults to stdin. It's necessary for ``serialize`` and
    ``upsert``, and silently ignored for ``{fetch,process}-readmes``.

    """
    env = wireup.env()
    args = parse_args(argv[1:])
    db = wireup.db(env)
    subcommands[args.command.replace('-', '_')](env, args, db)
