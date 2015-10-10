#!/usr/bin/env python -u
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.billing.payday import threaded_map
import csv, os, requests
import threading

url = 'https://api.balancedpayments.com/debits/{}/refunds'
balanced_api_secret = os.environ['BALANCED_API_SECRET']

inp = csv.reader(open('refunds.csv'))
out = csv.writer(open('refunds.completed.csv', 'w+'))
writelock = threading.Lock()

def refund(row):
    ts, id, amount, username, route_id = row
    response = requests.post( url.format(id)
                            , data={'amount': amount}
                            , auth=(balanced_api_secret, '')
                             )

    writelock.acquire()
    try:
        out.writerow((ts,id,amount,username,route_id,response.status_code,response.content))
    finally:
        writelock.release()
    return

threaded_map(refund, inp)
