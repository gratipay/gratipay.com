#!/usr/bin/env python -u
from __future__ import absolute_import, division, print_function, unicode_literals

import json, os, sys, traceback
from gratipay import wireup
from decimal import Decimal as D
from pprint import pprint
from gratipay.models.participant import Participant
from gratipay.models.exchange_route import ExchangeRoute

db = wireup.db(wireup.env())
dirname = os.path.join(os.path.dirname(__file__), 'balanced', 'transactions')


class UnknownExchange(Exception): pass
class UnknownCustomer(Exception): pass
class UnknownRoute(Exception): pass
class AmbiguousRoute(Exception): pass


def log(msg):
    print(msg, end=' | ')


def get_username(cur, customers, transaction):

    # First strategy: check known customers.
    username = customers.get(transaction['links']['customer'])
    if username:
        log('known customer')
        return username

    # Second strategy: blah
    raise UnknownCustomer()


def get_exchange_id(cur, transaction, username):

    # First strategy: use the one in the transaction!
    exchange_id = transaction['meta'].get('exchange_id')
    if exchange_id:
        log("exchange_id in transaction")
        return exchange_id

    # Second strategy: triangulate.
    params = dict( username = username
                 , amount   = D(transaction['amount']) / 100
                 , ts       = transaction['created_at']
                  )
    exchange_id = cur.one("""\
        SELECT id FROM exchanges
         WHERE participant = %(username)s
           AND amount + fee = %(amount)s
           AND ((   (%(ts)s::timestamptz - "timestamp") < interval '0'
                AND (%(ts)s::timestamptz - "timestamp") > interval '-15m'
                ) OR (
                    (%(ts)s::timestamptz - "timestamp") > interval '0'
                AND (%(ts)s::timestamptz - "timestamp") < interval '15m'
                ))
    """, params)
    if exchange_id:
        log("triangulated an exchange")
        return exchange_id

    raise UnknownExchange()


def get_route_id(cur, transaction, username, exchange_id):

    # First strategy: match on exchange id.
    route_id = cur.one("SELECT route FROM exchanges WHERE id=%s", (exchange_id,))
    if route_id:
        log("exchange has a route")
        return route_id

    # Second strategy: match on known cards.
    if not route_id:
        routes = cur.all( "SELECT * FROM exchange_routes "
                          "WHERE network='balanced-cc' and address='/cards/'||%s"
                        , (transaction['links']['source'],)
                         )
        if len(routes) == 1:
            route_id = routes[0].id
        elif len(routes) > 1:
            raise AmbiguousRoute()
    if route_id:
        log("card matches a route")
        return route_id

    # Third strategy: make a route!
    if not route_id:
        route = ExchangeRoute.insert( Participant.from_username(username)
                                    , 'balanced-cc'
                                    , '/cards/'+transaction['links']['source']
                                     )
        route_id = route.id
    if route_id:
        log("created a route")
        return route_id

    raise UnknownRoute()


def link_exchange_to_transaction(cur, transaction, customers):
    print("{created_at} | {description} | ".format(**transaction), end='')

    username = get_username(cur, customers, transaction)
    exchange_id = get_exchange_id(cur, transaction, username)
    status = transaction['status']
    route_id = get_route_id(cur, transaction, username, exchange_id)
    ref = transaction['id']

    existing = cur.one("SELECT * FROM exchanges WHERE id=%s", (exchange_id,), Exception)
    if existing.route:
        assert existing.route == route_id, exchange_id
        assert existing.status == status, exchange_id
        print("Already linked: {} & {}.".format(transaction['id'], exchange_id))
    else:
        assert existing.status in (None, status), exchange_id  # don't want to mutate status
        print("Linking {} to {}.".format(transaction['id'], exchange_id))
        cur.run( "UPDATE exchanges SET status=%s, route=%s, ref=%s WHERE id=%s"
               , (status, route_id, ref, exchange_id)
                )


def link_participant_to_customer(cur, transaction, customers):
    participant_id = transaction['meta'].get('participant_id')
    if participant_id:
        customer_id = transaction['links']['customer']
        if customer_id not in customers:
            import pdb; pdb.set_trace()  # not hit! :-(
            balanced_customer_href = '/customers/' + customer_id
            cur.run( 'UPDATE participants SET balanced_customer_href=%s WHERE id=%s'
                   , (balanced_customer_href, participant_id)
                    )
            print('Linked customer {} to participant {}.'
                  .format(balanced_customer_href, participant_id))


def walk(cur, visit):
    for filename in reversed(sorted(os.listdir(dirname))):
        data = json.load(open(os.path.join(dirname, filename)))

        for key in data:
            if key in ('links', 'meta'): continue
            transactions = reversed(data[key])

            if key == 'card_holds':
                continue  # We don't track these.

            if key != 'debits':
                continue  # Let's start with credit card charges.

            for transaction in transactions:
                try:
                    visit(cur, transaction)
                except KeyboardInterrupt:
                    raise
                except:
                    print("Exception! Thing:")
                    pprint(transaction)
                    print('-'*78)
                    traceback.print_exc(file=sys.stdout)
                    print('='*78)
    print()


def get_customers():
    customers = cur.all("SELECT balanced_customer_href, username FROM participants "
                        "WHERE balanced_customer_href is not null")
    return {rec[0][len('/customers/'):]: rec[1] for rec in customers}


with db.get_cursor() as cur:
    customers = get_customers()
    walk(cur, lambda *a: link_exchange_to_transaction(*a, customers=customers))
    raise Exception  # trigger rollback
