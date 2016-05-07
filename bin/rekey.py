#!/usr/bin/env python2
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay import wireup

env = wireup.env()
db = wireup.db(env)
wireup.crypto(env)

print("{} record(s) rekeyed.".format(0))  # stubbed until we have something to rekey
