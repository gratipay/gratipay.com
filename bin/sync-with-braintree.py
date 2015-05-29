#!/usr/bin/env python
from __future__ import print_function

import csv
import sys

import braintree
from gratipay import wireup


env = wireup.env()
billing = wireup.billing(env)
db = wireup.db(env)


try:
    fp = open(sys.argv[1])
except IndexError:
    fp = sys.stdin


for rec in csv.reader(fp):
    customer_id = rec[0]
    card_id = rec[8]

    if not card_id.startswith('CC'):
        pass    # a card vaulted directly at Braintree -- ensure knit to participant?

    print(customer_id, card_id)
