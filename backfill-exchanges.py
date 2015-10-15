#!/usr/bin/env python -u
from __future__ import absolute_import, division, print_function, unicode_literals

import csv
import os
import sys
import traceback
from collections import defaultdict
from datetime import datetime
from decimal import Decimal as D
from pprint import pprint

import pytz
from gratipay import wireup

db = wireup.db(wireup.env())
dirname = os.path.join(os.path.dirname(__file__), 'balanced', 'transactions')


class UnknownExchange(Exception):
    def __str__(self):
        return "\n\n{}".format(self.args[0])

class UnknownCustomer(Exception): pass
class UnknownRoute(Exception): pass
class AmbiguousCustomer(Exception): pass
class AmbiguousRoute(Exception): pass


class CountsOff(Exception):
    def __str__(self):
        msg, counts = self.args
        out = [msg]
        cur = ''
        for name, val in sorted(counts.__dict__.items()):
            if name[0] != cur:
                cur = name[0]
                out.append('')
            out.append("{:<26} {:>5}".format(name, val))
        return '\n'.join(out)


class Counts(object):
    def __init__(self):
        self.voided = 0

        self.customer_known = 0
        self.customer_unknown = 0

        self.exchange_in_transaction = 0
        self.exchange_triangulated = 0
        self.exchange_unknown = 0

        self.route_in_exchange = 0
        self.route_ambiguous = 0
        self.route_matched_via_card = 0
        self.route_matched_via_customer = 0
        self.route_ambiguous_customer = 0
        self.route_created = 0
        self.route_unknown = 0

        self.z_linking_now = 0

        self.z_n = 0


    def check(self):
        n = sum(( self.z_linking_now
                , self.customer_unknown
                , self.exchange_unknown
                , self.route_ambiguous
                , self.route_ambiguous_customer
                , self.route_unknown
                 ))
        if self.z_n != n:
            raise CountsOff("Total N is out from {}.".format(n), counts)

        ncustomers = sum((self.z_n,))
        nexchanges = sum(( self.exchange_in_transaction
                         , self.exchange_triangulated
                         , self.exchange_unknown
                          ))
        if ncustomers != nexchanges:
            raise CountsOff( "Customer count ({}) doesn't match exchange count ({})."
                             .format(ncustomers, nexchanges)
                           , counts
                            )


        nexchanges = sum(( self.exchange_in_transaction
                         , self.exchange_triangulated
                          ))
        nroutes = sum(( self.route_in_exchange
                      , self.route_ambiguous
                      , self.route_matched_via_card
                      , self.route_matched_via_customer
                      , self.route_ambiguous_customer
                      , self.route_created
                      , self.route_unknown
                       ))
        if nexchanges != nroutes:
            raise CountsOff( "Exchange count ({}) doesn't match route count ({})."
                             .format(nexchanges, nroutes)
                           , counts
                            )


def log(msg, w=0):
    print("{msg:<{w}}".format(msg=msg, w=w), end=' | ')


def get_exchange_id(cur, transaction, status, counts):
    if status == 'succeeded':
        amount = transaction['settlement_amount']
    else:
        assert status == 'failed'
        amount = transaction['amount_authorized']

    # First strategy: triangulate.
    params = dict( user_id   = transaction['participant_id']
                 , amount    = D(amount)
                 , ts        = transaction['created_at']
                  )
    mogrified = cur.mogrify("""\
        SELECT id FROM exchanges
         WHERE participant = (SELECT username FROM participants WHERE id=%(user_id)s)
           AND amount + fee = %(amount)s
           AND ((   (%(ts)s::timestamptz - "timestamp") < interval '0'
                AND (%(ts)s::timestamptz - "timestamp") > interval '-15m'
                ) OR (
                    (%(ts)s::timestamptz - "timestamp") > interval '0'
                AND (%(ts)s::timestamptz - "timestamp") < interval '15m'
                ))
    """, params)
    exchange_id = cur.one(mogrified)
    if exchange_id:
        counts.exchange_triangulated += 1
        log("triangulated an exchange", 26)
        return exchange_id

    counts.exchange_unknown += 1
    raise UnknownExchange(mogrified)


def get_route_id(cur, transaction, counts, exchange_id):

    # First strategy: match on exchange id.
    route_id = cur.one("SELECT route FROM exchanges WHERE id=%s", (exchange_id,))
    if route_id:
        counts.route_in_exchange += 1
        log("exchange has a route", 22)
        return route_id

    counts.route_unknown += 1
    raise UnknownRoute()


statuses = { 'settled': 'succeeded'
           , 'processor_declined': 'failed'
           , 'gateway_rejected': 'failed'
            }

def link_exchange_to_transaction(cur, transaction, customers, counts):
    print("{created_at} | {transaction_id:>6} | {participant_id:>6} | "
          .format(**transaction), end='')
    counts.z_n += 1

    status = statuses[transaction['transaction_status']]
    exchange_id = get_exchange_id(cur, transaction, status, counts)
    route_id = get_route_id(cur, transaction, counts, exchange_id)
    ref = transaction['transaction_id']

    existing = cur.one("SELECT * FROM exchanges WHERE id=%s", (exchange_id,), Exception)
    assert existing.route == route_id, exchange_id
    assert existing.status == status, exchange_id
    counts.z_linking_now += 1
    print("Linking {} & {}.".format(ref, exchange_id))
    cur.run( "UPDATE exchanges SET ref=%s WHERE id=%s", (ref, exchange_id))

    counts.check()


def log_exc(transaction):
    print("Exception! Transaction:")
    pprint(transaction)
    print('-'*78)
    traceback.print_exc(file=sys.stdout)
    print('='*78)


def get_customers():
    customers = cur.all("SELECT braintree_customer_id, username FROM participants "
                        "WHERE braintree_customer_id is not null")
    out = defaultdict(list)
    for braintree_customer_id, username in customers:
        out[braintree_customer_id].append(username)
    return out


def get_created_at(t):
    _date, _time = t['created_datetime'].split()
    month, day, year = map(int, _date.split('/'))
    hours, minutes, seconds = map(int, _time.split(':'))
    assert t['created_timezone'] == 'CDT'
    central = pytz.timezone('US/Central')
    d = datetime(year, month, day, hours, minutes, seconds)
    localized = central.localize(d)
    utc = localized.astimezone(pytz.utc)
    return str(utc)


with db.get_cursor() as cur:
    try:
        customers = get_customers()
        counts = Counts()
        transactions = csv.reader(open('balanced/refund/braintree.transactions.csv'))
        headers = [header.lower().replace(' ', '_') for header in transactions.next()]
        for row in transactions:
            transaction = dict(zip(headers, row))
            if transaction['transaction_status'] == 'voided':
                # We don't track holds that we voided entirely.
                counts.voided += 1
                print(counts.voided, file=sys.stderr)
                continue
            transaction['created_at'] = get_created_at(transaction)
            try:
                link_exchange_to_transaction(cur, transaction, customers, counts)
            except:
                log_exc(transaction)
                raise SystemExit()
    finally:
        print('Rolling back ...')
        cur.connection.rollback()
