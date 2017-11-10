#!/usr/bin/env python
from __future__ import absolute_import, division, print_function, unicode_literals

import sys
import commands


def title(title):
    print(title)
    print("-"*34)

def report(filename, *patterns):
    N = 0
    for pattern in patterns:
        n = int(commands.getoutput('grep "{}" {} | wc -l'.format(pattern, filename)))
        N += n
        print("{:<28} {:>5}".format(pattern, n))
    print("{:<28} {:>5}".format('', N))


report( sys.argv[1] if len(sys.argv) > 1 else 'backfill.log'
      , 'IMPOSSIBLE!!!!!!!!!!!$'
      , 'Eep! Guess failed!$'
      , 'all set!$'
      , 'yes$'
      , 'no$'
      , 'missing ref and status!$'
      , 'mismatched ref and status!$'
      , 'missing ref!$'
      , 'mismatched ref!$'
      , 'missing status!$'
      , 'mismatched status!$'
       )
