#!/usr/bin/env python
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay import wireup


db = wireup.db(wireup.env())


def get_participants(cur):
    return cur.all("SELECT participants.*::participants FROM participants WHERE balance > 0 LIMIT 10")


def get_refund(cur, participant):
    exchanges = cur.all("SELECT * FROM exchanges WHERE participant=%s", (participant.username,))
    payments = cur.all("SELECT * FROM payments WHERE participant=%s", (participant.username,))
    transfers = cur.all( "SELECT * FROM transfers "
                         "WHERE (tipper=%(username)s OR tippee=%(username)s)"
                       , dict(username=participant.username)
                        )
    get_timestamp = lambda t: t['timestamp']
    transactions = sorted(exchanges+payments+transfers, key=get_timestamp, reverse=True)
    balance = participant.balance
    for t in transactions:
        if 'fee' in t:
            if t['status'] == 'failed':
                continue
            if t['amount'] > 0:
                kind = 'cc'
                assert t['status'] in (None, 'succeeded')
                balance -= t['amount']
            else:
                kind = 'ba'
                balance -= t['amount'] - t['fee']
        elif 'direction' in t:
            if t['direction'] == 'to-participant':
                kind = 'take'
                balance -= t['amount']
            else:
                kind = 'payment'
                assert t['direction'] == 'to-team'
                balance += t['amount']
        else:
            t['kind'] = 'transfer'
            if t['tippee'] == participant.username:
                kind = 'tip-received'
                balance -= t['amount']
            else:
                kind = 'tip-given'
                balance += t['amount']

        yield {'balance': _balance, 'kind': kind, 'timestamp': str(t['timestamp'])}
        if balance <= 0 or kind == 'deposit':
            break


def process_participant(cur, participant):
    print()
    print(participant.username)
    print('='*70)

    for t in get_transactions(cur, participant):
        print('{timestamp:<32} {kind:<12} {balance:>5}'.format(**t))


with db.get_cursor(back_as=dict) as cur:
    try:
        for participant in get_participants(cur):
            process_participant(cur, participant)
    finally:
        print('Rolling back ...')
        cur.connection.rollback()
