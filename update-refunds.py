#!/usr/bin/env python
from __future__ import absolute_import, division, print_function, unicode_literals

import json, os, sys
from pprint import pprint
from gratipay import wireup
from decimal import Decimal as D

balance = 0
dirname = os.path.join(os.path.dirname(__file__), 'balanced', 'transactions')
db = wireup.db(wireup.env())

def get_exchange_id(ref, amount):
    with db.get_cursor() as cur:
        mogrified = cur.mogrify("""

            SELECT id
              FROM exchanges
             WHERE participant=(SELECT participant FROM exchanges WHERE ref=%s)
               AND amount=%s
               AND status='pending'
               AND note like 'refund of advance payment%%'

        """, (ref, amount))
        return cur.one(mogrified, default=NotImplementedError)

for filename in reversed(sorted(os.listdir(dirname))):
    if not filename.startswith('30'): continue
    data = json.load(open(os.path.join(dirname, filename)))

    for key in data:
        if key != 'refunds': continue

        for transaction in reversed(data[key]):
            if transaction['created_at'] < '2015-10-10': continue
            if transaction['status'] == 'failed':
                pprint(transaction, file=sys.stderr)
                continue
            assert transaction['status'] == 'succeeded'
            amount = -(D(transaction['amount']) / 100)
            print(transaction['created_at'], transaction['links']['debit'], amount, transaction['id'], end=' ')
            exchange_id = get_exchange_id(transaction['links']['debit'], amount)
            print(exchange_id)
            db.run("update exchanges set ref=%s, status=%s "
                   "where id=%s", (transaction['id'], transaction['status'], exchange_id))
