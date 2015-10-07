#!/usr/bin/env python
from __future__ import absolute_import, division, print_function, unicode_literals

import commands


def title(title):
    print(title)
    print("-"*34)

def report(*patterns):
    N = 0
    for pattern in patterns:
        n = int(commands.getoutput('grep "{}" backfill.log | wc -l'.format(pattern)))
        N += n
        print("{:<28} {:>5}".format(pattern, n))
    print("{:<28} {:>5}".format('', N))


title("Hi-level")
report("Linking", "Already linked", "raise UnknownCustomer", "raise UnknownExchange",
       "raise UnknownRoute")

title("Participants")
report("known customer", "raise UnknownCustomer")

title("Exchanges")
report("exchange_id in transaction", "triangulated an exchange", "raise UnknownExchange")

title("Routes")
report("exchange has a route", "card matches a route", "created a route", "raise UnknownRoute")

title("Check")
report("^201\d-")
