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

reader = csv.reader(fp)
reader.next()   # header row

ndirect = 0
norphan = 0

for rec in reader:
    customer_id = rec[0]
    card_id = rec[8]

    if not card_id.startswith('CC'):
        # a card vaulted directly at Braintree -- ensure they're already knit to a participant?
        ndirect += 1

    if not (customer_id.startswith('AC') or customer_id.startswith('CU')):
        # a Balanced card that came with no customer_id -- how can we knit to a participant?
        norphan += 1

    print(customer_id, card_id)

print()
print("{:<30} {:>5}".format("Vaulted directly at Braintree:", ndirect))
print("{:<30} {:>5}".format("Orphaned:", norphan))
