#!/usr/bin/env python -u
from __future__ import absolute_import, division, print_function, unicode_literals

import csv
from gratipay import wireup
from decimal import Decimal

db = wireup.db(wireup.env())
inp = csv.reader(open('balanced/refund/refunds.completed.csv'))

for ts, id, amount, username, route_id, status_code, content in inp:
    if status_code != '201': continue
    balance = db.one('select balance from participants where username=%s', (username,))
    amount = Decimal('-' + amount[:-2] + '.' + amount[-2:])
    print("{:>6} {:>6} {}".format(balance, amount, username))
    assert balance == -amount
    db.run('update participants set balance=0 where username=%s', (username,))
