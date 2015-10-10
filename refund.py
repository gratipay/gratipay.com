#!/usr/bin/env python -u
from __future__ import absolute_import, division, print_function, unicode_literals

import sys
from collections import defaultdict
from decimal import Decimal

from gratipay import wireup


db = wireup.db(wireup.env())


def get_participants(cur):
    return cur.all("SELECT participants.*::participants FROM participants WHERE balance > 0")


def process_participant(cur, participant, counts):
    exchanges = cur.all("SELECT e.*, er.network FROM exchanges e "
                        "LEFT JOIN exchange_routes er ON e.route = er.id "
                        "WHERE e.participant=%s", (participant.username,))
    payments = cur.all("SELECT * FROM payments WHERE participant=%s", (participant.username,))
    transfers = cur.all( "SELECT * FROM transfers "
                         "WHERE (tipper=%(username)s OR tippee=%(username)s)"
                       , dict(username=participant.username)
                        )
    get_timestamp = lambda t: t['timestamp']
    transactions = sorted(exchanges+payments+transfers, key=get_timestamp, reverse=True)
    current_balance = balance = participant.balance
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

    params = dict( timestamp = ''
                 , network = ''
                 , exchange_id = ''
                 , exchange_amount = ''
                 , refund_amount = 0
                 , username = participant.username
                 , yesno = ' no'
                  )
    if exchange:
        params['refund_amount'] = min(current_balance, exchange['amount'])
        params.update( timestamp = str(exchange['timestamp'])
                     , network = exchange['network'] if exchange['network'] else '<unknown>'
                     , exchange_id = exchange['id']
                     , exchange_amount = exchange['amount']
                     , yesno = 'yes'
                      )
        counts.total += params['refund_amount']
        counts.by_network[params['network']] += params['refund_amount']
        if exchange['network'] == 'balanced-cc':
            print('{},{},{},{},{}'.format( params['timestamp']
                                         , exchange['ref']
                                         , str(params['refund_amount']).replace('.', '')
                                         , exchange['participant']
                                         , exchange['route']
                                          ))
    print('{timestamp:<33} {yesno} {exchange_id:>6} {network:>16} {exchange_amount:>7} '
          '{refund_amount:>7} {username}'
          .format(**params), file=sys.stderr)


class Counts(object):
    total = 0
    by_network = defaultdict(lambda: Decimal('0.00'))
    def __str__(self):
        out = []
        for key, val in self.by_network.items():
            out.append('{:<12} {:>8}'.format(key, val))
        out.append('{:<12} {:>8}'.format('', self.total))
        return '\n'.join(out)

with db.get_cursor(back_as=dict) as cur:
    try:
        counts = Counts()
        for participant in get_participants(cur):
            process_participant(cur, participant, counts)
        print(counts, file=sys.stderr)
    finally:
        cur.connection.rollback()
