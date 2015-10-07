#!/usr/bin/env python -u
from __future__ import absolute_import, division, print_function, unicode_literals

import json, os, sys, traceback
from collections import defaultdict
from gratipay import wireup
from decimal import Decimal as D
from pprint import pprint
from gratipay.models.participant import Participant
from gratipay.models.exchange_route import ExchangeRoute

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
            out.append("{:<23} {:>5}".format(name, val))
        return '\n'.join(out)


class Counts(object):
    def __init__(self):
        self.customer_known = 0
        self.customer_unknown = 0

        self.exchange_in_transaction = 0
        self.exchange_triangulated = 0
        self.exchange_unknown = 0

        self.route_in_exchange = 0
        self.route_ambiguous = 0
        self.route_matched_to_card = 0
        self.route_ambiguous_customer = 0
        self.route_created = 0
        self.route_unknown = 0

        self.z_linked_already = 0
        self.z_linking_now = 0

        self.z_n = 0


    def check(self):
        n = sum(( self.z_linking_now
                , self.z_linked_already
                , self.customer_unknown
                , self.exchange_unknown
                , self.route_ambiguous
                , self.route_ambiguous_customer
                , self.route_unknown
                 ))
        if self.z_n != n:
            raise CountsOff("Total N is out from {}.".format(n), counts)

        ncustomers = sum((self.customer_known,))
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
                      , self.route_matched_to_card
                      , self.route_ambiguous_customer
                      , self.route_created
                      , self.route_unknown
                       ))
        if nexchanges != nroutes:
            raise CountsOff( "Exchange count ({}) doesn't match route count ({})."
                             .format(nexchanges, nroutes)
                           , counts
                            )


def log(msg):
    print(msg, end=' | ')


def get_usernames(cur, transaction, customers, counts):

    # First strategy: check known customers.
    usernames = customers.get(transaction['links']['customer'])
    if usernames:
        counts.customer_known += 1
        log('known customer ({} participant(s))'.format(len(usernames)))
        return usernames

    # Second strategy: blah
    counts.customer_unknown += 1
    raise UnknownCustomer()


def get_exchange_id(cur, transaction, counts, usernames):

    # First strategy: use the one in the transaction!
    exchange_id = transaction['meta'].get('exchange_id')
    if exchange_id:
        counts.exchange_in_transaction += 1
        log("exchange_id in transaction")
        return exchange_id

    # Second strategy: triangulate.
    params = dict( usernames = usernames
                 , amount    = D(transaction['amount']) / 100
                 , ts        = transaction['created_at']
                  )
    mogrified = cur.mogrify("""\
        SELECT id FROM exchanges
         WHERE participant = ANY(%(usernames)s)
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
        log("triangulated an exchange")
        return exchange_id

    counts.exchange_unknown += 1
    raise UnknownExchange(mogrified)


def get_route_id(cur, transaction, counts, usernames, exchange_id):

    # First strategy: match on exchange id.
    route_id = cur.one("SELECT route FROM exchanges WHERE id=%s", (exchange_id,))
    if route_id:
        counts.route_in_exchange += 1
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
            counts.route_ambiguous += 1
            raise AmbiguousRoute()
    if route_id:
        counts.route_matched_to_card += 1
        log("card matches a route")
        return route_id

    # Third strategy: make a route!
    if not route_id:
        if len(usernames) > 1:
            # XXX Pick the username of the non-archived participant (or the one that makes sense
            # in the special case).
            counts.route_ambiguous_customer += 1
            raise AmbiguousCustomer()
        username = usernames[0]
        route = ExchangeRoute.insert( Participant.from_username(username)
                                    , 'balanced-cc'
                                    , '/cards/'+transaction['links']['source']
                                    , cursor=cur
                                     )
        route_id = route.id
    if route_id:
        counts.route_created += 1
        log("created a route")
        return route_id

    counts.route_unknown += 1
    raise UnknownRoute()


def link_exchange_to_transaction(cur, transaction, customers, counts):
    print("{created_at} | {description} | ".format(**transaction), end='')
    counts.z_n += 1

    usernames = get_usernames(cur, transaction, customers, counts)
    exchange_id = get_exchange_id(cur, transaction, counts, usernames)
    status = transaction['status']
    route_id = get_route_id(cur, transaction, counts, usernames, exchange_id)
    ref = transaction['id']

    existing = cur.one("SELECT * FROM exchanges WHERE id=%s", (exchange_id,), Exception)
    if existing.route:
        assert existing.route == route_id, exchange_id
        assert existing.status == status, exchange_id
        counts.z_linked_already += 1
        print("Already linked: {} & {}.".format(transaction['id'], exchange_id))
    else:
        assert existing.status in (None, status), exchange_id  # don't want to mutate status
        counts.z_linking_now += 1
        print("Linking {} to {}.".format(transaction['id'], exchange_id))
        cur.run( "UPDATE exchanges SET status=%s, route=%s, ref=%s WHERE id=%s"
               , (status, route_id, ref, exchange_id)
                )

    counts.check()


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


def log_exc(transaction):
    print("Exception! Thing:")
    pprint(transaction)
    print('-'*78)
    traceback.print_exc(file=sys.stdout)
    print('='*78)


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
                if transaction['links']['source'].startswith('BA'):
                    continue  # Filter out escrow shuffles (we didn't do any other ACH debits).
                try:
                    visit(cur, transaction)
                except KeyboardInterrupt:
                    raise
                except CountsOff:
                    log_exc(transaction)
                    raise
                except:
                    log_exc(transaction)
    print()


def get_customers():
    customers = cur.all("SELECT balanced_customer_href, username FROM participants "
                        "WHERE balanced_customer_href is not null")
    out = defaultdict(list)
    for balanced_customer_href, username in customers:
        customer_id = balanced_customer_href[len('/customers/'):]
        out[customer_id].append(username)
    return out


with db.get_cursor() as cur:
    try:
        customers = get_customers()
        counts = Counts()
        walk(cur, lambda *a: link_exchange_to_transaction(*a, counts=counts, customers=customers))
    finally:
        print('Rolling back ...')
        cur.connection.rollback()
