#!/usr/bin/env python -u
from __future__ import absolute_import, division, print_function, unicode_literals

import csv, os, requests

url = 'https://api.balancedpayments.com/debits/{}/refunds'
username = os.environ['BALANCED_API_USER']

inp = csv.reader(open('refunds.csv'))
inp.next()  # headers

out = csv.writer(open('refunds.completed.csv', 'w+'))
out.writerow(('ts', 'id', 'amount', 'code', 'body'))

for ts, id, amount in inp:
    response = requests.post( url.format(id)
                            , data={'amount': amount}
                            , auth=(username, '')
                             )
    out.writerow((ts,id,amount,response.status_code,response.content))
