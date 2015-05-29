#!/usr/bin/env python
from __future__ import print_function

import csv
import sys

import braintree
import requests
import datetime
import threading
from gratipay import wireup
from gratipay.billing.payday import threaded_map
from gratipay.models.exchange_route import ExchangeRoute
from postgres.cursors import TooMany


env = wireup.env()
billing = wireup.billing(env)
db = wireup.db(env)


try:
    fp = open(sys.argv[1])
except IndexError:
    fp = sys.stdin

reader = csv.reader(fp)
reader.next()   # header row


def is_removed(card_id):
    """Given a Balanced card id, return a boolean indicating whether it is `status: removed`.
    """
    response = requests.get( 'https://api.balancedpayments.com/cards/{}'.format(card_id)
                           , auth=(env.balanced_api_secret, '')
                            )
    if response.status_code != 200:
        log("Failure hitting Balanced ...", file=sys.stderr)
        log(response.status_code, response.body, file=sys.stderr)
        return False
    cards = response.json()['cards']
    assert len(cards) == 1
    return cards[0]['can_debit'] == False


def get_participant_from_card_id(card_id):
    p = db.all( "SELECT p.*::participants FROM participants p "
                "JOIN current_exchange_routes cer ON p.id = cer.participant "
                "WHERE address=%s AND network='balanced-cc'"
              , ("/cards/{}".format(card_id),)
               )
    return _get_participant(card_id, p)

def get_participant_from_customer_id(customer_id):
    p = db.all( "SELECT p.*::participants FROM participants p "
                "WHERE balanced_customer_href=%s "
              , ("/customers/{}".format(customer_id),)
               )
    return _get_participant(customer_id, p)

def _get_participant(_id, p):
    n = len(p)
    if n < 1:
        log("UNKNOWN: {}".format(_id,))
        return
    elif n > 1:
        p = [x for x in p if x.claimed_time is not None]
        assert len(p) == 1, TooMany([x.username for x in p], 1, 1)
    p = p[0]

    def _delete(reason):
        log("{}: {}={} {}".format(reason, p.id, p.username, _id))
        return

    if p.braintree_customer_id is not None:
        if ExchangeRoute.from_network(p, 'braintree-cc'):
            return _delete("MIGRATED THEMSELVES")
    elif p.is_suspicious is True:
        return _delete("SUSPICIOUS ACCOUNT")
    elif p.is_closed:
        return _delete("CLOSED ACCOUNT")
    elif p.claimed_time is None:
        return _delete("ARCHIVED ACCOUNT")

    return p


_log_lock = threading.Lock()
def log(*a, **kw):
    with _log_lock:
        ts = str(datetime.datetime.utcnow()).split()[1]
        print("{} {}".format(threading.current_thread().ident, ts), *a, **kw)


def process_record(rec):
    customer_id = rec[0]
    card_id = rec[8]

    if not card_id.startswith('CC'):
        # a card freshly vaulted at Braintree -- ignore it
        return

    elif is_removed(card_id):
        # a Balanced card that never should've made it into Braintree -- get rid of it!
        log("CARD {} REMOVED AT BALANCED (CUSTOMER: {})".format(card_id, customer_id))
        p = None

    elif not (customer_id.startswith('AC') or customer_id.startswith('CU')):
        # a Balanced card that came with no customer_id -- can we find a participant anyway?
        log("ORPHANED CARD {} FOR {}".format(card_id, customer_id))
        #p = get_participant_from_card_id(card_id)  It's no use. Don't waste the time. :-(
        p = None

    else:
        # a live card that came from Balanced with a proper customer_id -- yessss!
        log("GOOD CARD {} FOR {}".format(card_id, customer_id))
        p = get_participant_from_customer_id(customer_id)

    if p is None:
        braintree.PaymentMethod.delete(card_id)
        log("DELETED CARD {} FOR {}".format(card_id, customer_id))
    else:
        braintree.Customer.update(customer_id, {'custom_fields': {'participant_id': p.id}})
        db.run( "UPDATE participants SET braintree_customer_id=%s WHERE username=%s"
              , (customer_id, p.username)
               )
        ExchangeRoute.insert(p, 'braintree-cc', card_id)
        log("SYNCED {} WITH {}={} (CARD: {})".format(customer_id, p.id, p.username, card_id))


if __name__ == '__main__':
    threaded_map(process_record, reader, threads=10)
