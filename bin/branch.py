#!/usr/bin/env python
from __future__ import print_function

import csv
import sys
import traceback
from postgres.cursors import TooMany
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

    try:
        p = db.all( "SELECT p.*::participants FROM participants p "
                    "WHERE balanced_customer_href=%s "
                  , ("/customers/{}".format(customer_id),)
                   )
        n = len(p)
        if n < 1:
            print("SKIPPING UNKNOWN ACCOUNT: {}".format(customer_id,))
            continue
        elif n > 1:
            p = [x for x in p if x.claimed_time is not None]
            assert len(p) == 1, TooMany([x.username for x in p], 1, 1)
        p = p[0]

        if p.braintree_customer_id is not None:
            print("SKIPPING ALREADY MIGRATED ACCOUNT: {} {}".format(p.username, customer_id))
            continue
        if p.is_suspicious is True:
            print("SKIPPING SUSPICIOUS ACCOUNT: {} {}".format(p.username, customer_id))
            continue
        if p.is_closed:
            print("SKIPPING CLOSED ACCOUNT: {} {}".format(p.username, customer_id))
            continue
        if p.claimed_time is None:
            print("SKIPPING ARCHIVED ACCOUNT: {} {}".format(p.username, customer_id))
            continue

    except KeyboardInterrupt:
        raise
    except:
        print("FAILURE FOR {} ({})".format(customer_id, card_id))
        print(traceback.format_exc())
        continue

    if 0:
        er = ExchangeRoute.insert(p, 'braintree-cc', card_id)
        db.run( "UPDATE participants SET braintree_customer_id=%s, balanced_customer_href=null"
                "WHERE username=%s"
              , (customer_id, p.username)
               )

    print("SYNCED {} -> {} ({}) {}"
                               .format(p.balanced_customer_href, customer_id, card_id, p.username))
