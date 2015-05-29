#!/usr/bin/env python
from __future__ import print_function

import csv
import sys

import requests
import threading
from gratipay import wireup
from gratipay.billing.payday import threaded_map


env = wireup.env()
billing = wireup.billing(env)
db = wireup.db(env)


try:
    fp = open(sys.argv[1])
except IndexError:
    fp = sys.stdin

reader = csv.reader(fp)
reader.next()   # header row


def is_removed(card_id):
    """Given a Balanced card id, return a boolean indicating whether it is `status: removed`.
    """
    response = requests.get( 'https://api.balancedpayments.com/cards/{}'.format(card_id)
                           , auth=(env.balanced_api_secret, '')
                            )
    if response.status_code != 200:
        log("Failure hitting Balanced ...", file=sys.stderr)
        log(response.status_code, response.body, file=sys.stderr)
        return False
    cards = response.json()['cards']
    assert len(cards) == 1
    return cards[0]['can_debit'] == False


nfresh = 0
norphan = 0
nremoved = 0
ngood = 0

_log_lock = threading.Lock()
def log(*a, **kw):
    global nfresh, norphan, nremoved, ngood
    with _log_lock:
        if a[0].startswith('FRESH'):        nfresh += 1
        elif a[0].startswith('ORPHAN'):     norphan += 1
        elif a[0].startswith('DELETED'):    nremoved += 1
        else:                               ngood += 1
        print(*a, **kw)


def process_record(rec):
    customer_id = rec[0]
    card_id = rec[8]

    if not card_id.startswith('CC'):
        # a card vaulted directly at Braintree -- ensure they're already knit to a participant?
        log("FRESH CARD {} FOR {}".format(card_id, customer_id))

    elif not (customer_id.startswith('AC') or customer_id.startswith('CU')):
        # a Balanced card that came with no customer_id -- how can we knit to a participant?
        log("ORPHANED CARD {} FOR {}".format(card_id, customer_id))

    elif is_removed(card_id):
        # a Balanced card that never should've made it into Braintree -- get rid of it!
        #braintree.PaymentMethod.delete(card_id)
        log("DELETED {} FOR {}".format(card_id, customer_id))

    else:
        log("FINDING PARTICIPANT FOR {}".format(customer_id))


threaded_map(process_record, reader, threads=10)


print()
print("{:<16} {:>5}".format("Freshly vaulted:", nfresh))
print("{:<16} {:>5}".format("Orphaned:", norphan))
print("{:<16} {:>5}".format("Removed:", nremoved))
print("{:<16} {:>5}".format("Good:", ngood))
