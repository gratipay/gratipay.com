#!/usr/bin/env python -u
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay import wireup


db = wireup.db(wireup.env())


def get_participants(cur):
    return cur.all("SELECT participants.*::participants FROM participants WHERE balance > 0")


def process_participant(cur, participant):
    exchanges = cur.all( "SELECT * FROM exchanges JOIN exchange_routes WHERE participant=%s"
                       , (participant.username,)
                        )
    payments = cur.all("SELECT * FROM payments WHERE participant=%s", (participant.username,))
    transfers = cur.all( "SELECT * FROM transfers "
                         "WHERE (tipper=%(username)s OR tippee=%(username)s)"
                       , dict(username=participant.username)
                        )
    get_timestamp = lambda t: t['timestamp']
    transactions = sorted(exchanges+payments+transfers, key=get_timestamp, reverse=True)
    amount = balance = participant.balance
    exchange = None
    for t in transactions:
        if balance <= 0: break
        if 'fee' in t:
            if t['status'] == 'failed':
                continue
            if t['amount'] > 0:
                assert t['status'] in (None, 'succeeded')
                exchange = t
                break
            else:
                balance -= t['amount'] - t['fee']
        elif 'direction' in t:
            if t['direction'] == 'to-participant':
                balance -= t['amount']
            else:
                assert t['direction'] == 'to-team'
                balance += t['amount']
        else:
            if t['tippee'] == participant.username:
                balance -= t['amount']
            else:
                balance += t['amount']
        #print('{timestamp:<32} {kind:<12} {balance:>5}'.format(**t))

    params = dict( timestamp = t['timestamp']
                 , refund_amount = amount
                 , username = participant.username
                 , exchange_id = ''
                 , exchange_amount = ''
                 , yesno = ' no'
                  )
    if exchange:
        params['exchange_id'] = exchange['id']
        params['exchange_amount'] = exchange['amount']
        params['yesno'] = 'yes'
        if amount > exchange['amount']:
            params['yesno'] = 'BAD'
    print('{timestamp} {yesno} {exchange_id:>6} {refund_amount:>7} {exchange_amount:>7} {username}'
          .format(**params))


with db.get_cursor(back_as=dict) as cur:
    try:
        for participant in get_participants(cur):
            process_participant(cur, participant)
    finally:
        cur.connection.rollback()
