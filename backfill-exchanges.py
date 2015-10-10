#!/usr/bin/env python -u
from __future__ import absolute_import, division, print_function, unicode_literals

import json, os, sys, traceback
from collections import defaultdict
from gratipay import wireup
from decimal import Decimal as D
from pprint import pprint
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
            out.append("{:<24} {:>5}".format(name, val))
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
        self.route_matched_via_card = 0
        self.route_matched_via_customer = 0
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


def get_usernames(cur, transaction, customers, counts):

    # First strategy: check known customers.
    usernames = customers.get(transaction['links']['customer'])
    if usernames:
        counts.customer_known += 1
        log('known customer')
        log('participants: {}'.format(len(usernames)))
        return usernames

    # Second strategy: blah
    counts.customer_unknown += 1
    raise UnknownCustomer()


def get_exchange_id(cur, transaction, counts, usernames):

    # First strategy: use the one in the transaction!
    exchange_id = transaction['meta'].get('exchange_id')
    if exchange_id:
        counts.exchange_in_transaction += 1
        log("exchange_id in transaction", 26)
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
        log("triangulated an exchange", 26)
        return exchange_id

    counts.exchange_unknown += 1
    raise UnknownExchange(mogrified)


def resolve_route(cur, transaction, counts, routes, usernames):
    log('routes: {routes:<12}'.format(routes=', '.join(str(r.id) for r in routes)))

    nroutes = len(routes)
    if nroutes == 0:    return None
    elif nroutes == 1:  return routes[0].id
    assert nroutes == 2
    # Pick the route for the participant that was active at the time of the transaction.

    nusernames = len(usernames)
    assert nusernames in (1, 2), (usernames, routes)
    if nusernames == 1:
        counts.route_ambiguous += 1
        raise AmbiguousRoute()
    else:
        # See if we can assume it's a case of absorption.
        user_ids = [r.participant for r in routes]
        i2n = dict(cur.all( "SELECT id, username FROM participants WHERE id = ANY(%s)"
                          , (user_ids,)
                           ))
        assert sorted(i2n.values()) == sorted(usernames)
        u2r = {i2n[r.participant]: r.id for r in routes}

        keys = u2r.keys()
        absorption = cur.one("""\
            SELECT *
              FROM absorptions
             WHERE (archived_as=%(one)s AND absorbed_by=%(two)s)
                OR (archived_as=%(two)s AND absorbed_by=%(one)s)
        """, dict(one=keys[0], two=keys[1]))
        if absorption is None:
            counts.route_ambiguous += 1
            raise AmbiguousRoute()
        if transaction['created_at'] < str(absorption.timestamp).replace('+00:00', 'Z'):
            key = absorption.archived_as
        else:
            assert transaction['created_at'] > str(absorption.timestamp).replace('+00:00', 'Z')
            key = absorption.absorbed_by
        return u2r[key]


def get_route_id(cur, transaction, counts, usernames, exchange_id):

    # First strategy: match on exchange id.
    route_id = cur.one("SELECT route FROM exchanges WHERE id=%s", (exchange_id,))
    if route_id:
        counts.route_in_exchange += 1
        log("exchange has a route", 22)
        return route_id

    # Second strategy: match on known cards.
    if not route_id:
        routes = cur.all( "SELECT * FROM exchange_routes "
                          "WHERE network='balanced-cc' AND address='/cards/'||%s"
                        , (transaction['links']['source'],)
                         )
        route_id = resolve_route(cur, transaction, counts, routes, usernames)
    if route_id:
        counts.route_matched_via_card += 1
        log("card matches {}".format(route_id), 22)
        return route_id

    # Third strategy: match on usernames.
    if not route_id:
        routes = cur.all("""\
            SELECT *
              FROM exchange_routes
             WHERE network='balanced-cc' and participant in (
                    SELECT id
                      FROM participants
                     WHERE username=ANY(%s)
                   )
        """, (usernames,))
        route_id = resolve_route(cur, transaction, counts, routes, usernames)
    if route_id:
        counts.route_matched_via_customer += 1
        log("customer matches {}".format(route_id), 22)
        return route_id

    # Fourth strategy: make a route!
    if not route_id:
        if len(usernames) > 1:
            counts.route_ambiguous_customer += 1
            raise AmbiguousCustomer()
        username = usernames[0]
        participant = cur.one("SELECT participants.*::participants FROM participants "
                              "WHERE username=%s", (username,))
        route = ExchangeRoute.insert( participant
                                    , 'balanced-cc'
                                    , '/cards/'+transaction['links']['source']
                                    , cursor=cur
                                     )
        route_id = route.id
    if route_id:
        counts.route_created += 1
        log("created a route", 22)
        return route_id

    counts.route_unknown += 1
    raise UnknownRoute()


def link_exchange_to_transaction(cur, transaction, customers, counts):
    print("{created_at} | {description:>24} | ".format(**transaction), end='')
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
        cur.run( "UPDATE exchanges SET ref=%s WHERE id=%s", (ref, exchange_id))
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
    print("Exception! Transaction:")
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
