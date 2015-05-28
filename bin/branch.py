#!/usr/bin/env python
from __future__ import print_function

import csv
import sys
from gratipay.wireup import db, env
from gratipay.models.exchange_route import ExchangeRoute


DETAILS = 4
NAME = 7
CUSTOMER_ID = 1
CARD_ID = -1
CHECK = 6
db = db(env())

for row in csv.reader(sys.stdin):
    if row[DETAILS] != 'customer':
        continue
    assert row[CUSTOMER_ID] == row[CHECK], row

    customer_id = row[CUSTOMER_ID]
    card_id = row[CARD_ID]

    p = db.one( "SELECT p.*::participants FROM participants p WHERE balanced_customer_href=%s"
              , ("/customers/{}".format(customer_id),)
               )

    er = ExchangeRoute.insert(p, 'braintree-cc', card_id)
    db.run("UPDATE participants SET braintree_customer_id=%s", (customer_id,))

    print("{} -> {} ({}) {}".format(p.balanced_customer_href, customer_id, card_id, p.username))
