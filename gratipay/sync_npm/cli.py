# -*- coding: utf-8 -*-
"""Define the top-level function for the ``sync-npm`` cli.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import sys
import argparse

from gratipay import wireup
from gratipay.sync_npm import serialize, upsert


def parse_args(argv):
    p = argparse.ArgumentParser()
    p.add_argument('command', choices=['serialize', 'upsert'])
    p.add_argument('path', help='the path to the input file', nargs='?', default='/dev/stdin')
    return p.parse_args(argv)


subcommands = { 'serialize': serialize.main
              , 'upsert': upsert.main
               }


def main(argv=sys.argv):
    """This function is installed via an entrypoint in ``setup.py`` as
    ``sync-npm``.

    Usage::

      sync-npm {serialize,upsert} {<filepath>}

    ``<filepath>`` defaults to stdin.

    .. note:: Sphinx is expanding ``sys.argv`` in the parameter list. Sorry. :-/

    """
    env = wireup.env()
    args = parse_args(argv[1:])
    db = wireup.db(env)

    subcommands[args.command](env, args, db)
