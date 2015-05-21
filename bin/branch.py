#!/usr/bin/env python
from __future__ import print_function

import csv
import sys
from gratipay.wireup import db, env


DETAILS = 4
NAME = 7
CUSTOMER_ID = 1
CHECK = 6
db = db(env())

customers_cards = []

for row in csv.reader(sys.stdin):
    if row[DETAILS] != 'customer':
        continue
    assert row[CUSTOMER_ID] == row[CHECK], row

    customer_id = row[CUSTOMER_ID]
    card_id = row[CARD_ID]

    customers_cards.append((customer_id, card_id))


if 0:
    p = db.one("""\

            SELECT participants.*::participants
              FROM participants
             WHERE balanced_customer_id in %s
    """)

    ExchangeRoute.insert(p, 'braintree-cc', )

    db.run("UPDATE participants SET braintree_customer_id=")
