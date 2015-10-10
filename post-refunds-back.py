#!/usr/bin/env python -u
from __future__ import absolute_import, division, print_function, unicode_literals

import csv, os, requests

gratipay_base_url = 'https://gratipay.com'
gratipay_base_url = 'http://localhost:8537'
gratipay_api_key = os.environ['GRATIPAY_API_KEY']

inp = csv.reader(open('refunds.completed.csv'))

for ts, id, amount, username, route_id, status_code, content in inp:
    if status_code != '200': continue
    url = '{}/~{}/history/record-an-exchange'.format(gratipay_base_url, username)
    note = 'refund of advance payment; see https://medium.com/gratipay-blog/charging-in-arrears-18cacf779bee'

    data = { 'amount': amount[:-2] + '.' + amount[-2:]
           , 'fee': 0
           , 'note': note
           , 'status': 'pending'
           , 'route_id': route_id
            }
    response = requests.post(url, auth=(gratipay_api_key, ''), data=data)
    print(response.status_code, response.content)
