#!/usr/bin/env python -u
from __future__ import absolute_import, division, print_function, unicode_literals

import csv
from decimal import Decimal as D
from gratipay import wireup
from gratipay.models.exchange_route import ExchangeRoute
from gratipay.models.participant import Participant
from gratipay.billing.exchanges import record_exchange

db = wireup.db(wireup.env())
inp = csv.reader(open('refunds.completed.csv'))
note = 'refund of advance payment; see https://medium.com/gratipay-blog/18cacf779bee'

total = N = 0
for ts, id, amount, username, route_id, success, ref in inp:
    print('posting {} back for {}'.format(amount, username))
    assert success == 'True'
    total += D(amount)
    N += 1

    amount = D('-' + amount)
    route = ExchangeRoute.from_id(route_id)

    # Such a hack. :(
    rp = route.participant
    participant = Participant.from_id(rp) if type(rp) is long else rp
    route.set_attributes(participant=participant)

    exchange_id = record_exchange(db, route, amount, 0, participant, 'pending', note)
    db.run("update exchanges set ref=%s where id=%s", (ref, exchange_id))

print('posted {} back for {}'.format(total, N))
