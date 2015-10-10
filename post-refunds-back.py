#!/usr/bin/env python -u
from __future__ import absolute_import, division, print_function, unicode_literals

import csv
from gratipay import wireup
from gratipay.models.exchange_route import ExchangeRoute
from gratipay.models.participant import Participant
from gratipay.billing.exchanges import record_exchange

db = wireup.db(wireup.env())
inp = csv.reader(open('balanced/refund/refunds.completed.csv'))
note = 'refund of advance payment; see https://medium.com/gratipay-blog/charging-in-arrears-18cacf779bee'

for ts, id, amount, username, route_id, status_code, content in inp:
    if status_code != '201': continue
    amount = '-' + amount[:-2] + '.' + amount[-2:]
    print('posting {} back for {}'.format(amount, username))
    route = ExchangeRoute.from_id(route_id)
    rp = route.participant
    participant = Participant.from_id(rp) if type(rp) is long else rp  # Such a hack. :(
    route.set_attributes(participant=participant)
    record_exchange(db, route, amount, 0, participant, 'pending', note)
