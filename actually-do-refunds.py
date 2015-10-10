#!/usr/bin/env python -u
from __future__ import absolute_import, division, print_function, unicode_literals

import csv, os, requests

url = 'https://api.balancedpayments.com/debits/{}/refunds'
balanced_api_user = os.environ['BALANCED_API_USER']

inp = csv.reader(open('refunds.csv'))
out = csv.writer(open('refunds.completed.csv', 'w+'))

for ts, id, amount, username, route_id in inp:
    response = requests.post( url.format(id)
                            , data={'amount': amount}
                            , auth=(balanced_api_user, '')
                             )
    out.writerow((ts,id,amount,username,route_id,response.status_code,response.content))
