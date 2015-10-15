#!/usr/bin/env python -u
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.billing.payday import threaded_map
import csv
import threading
import braintree
from gratipay import wireup

wireup.billing(wireup.env())

inp = csv.reader(open('refunds.csv'))
out = csv.writer(open('refunds.completed.csv', 'w+'))
writelock = threading.Lock()

def refund(row):
    ts, id, amount, username, route_id = row
    result = braintree.Transaction.refund(id, amount)
    extra = result.transaction.id if result.is_success else result.message
    writelock.acquire()
    try:
        out.writerow((ts, id, amount, username, route_id, result.is_success, extra))
    finally:
        writelock.release()
    return

threaded_map(refund, inp)
