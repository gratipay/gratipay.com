#!/usr/bin/env python2 -u
"""Script for backfilling exchange status, route, and ref.

Symlink a directory of data at `./backfill` and then call like so:

    [gratipay] $ run_dammit defaults.env local.env -c env/bin/python backfill.py

Data files should be one per network (named `samurai`, `stripe`, etc), as CSVs
with these columns:

    username        ignored
    user_id         required    Gratipay participant.id
    address         optional    defaults to 'fake-deadbeef'
    exchange_id     optional    Gratipay exchanges.id; required for status == 'succeeded'
    amount          optional    transaction amount; required if exchange_id is empty
    ref             optional    defaults to 'fake-beeffeed'
    status          required    Gratipay exchanges.status: succeeded, failed, pending

For successfully backfilled exchanges (and routes), the script outputs the same
CSV as was input, with optional fields filled in. The script is idempotent (the
faked address and ref are hashed from other input values).

"""
from __future__ import absolute_import, division, print_function, unicode_literals

import csv
import os
import sha
import sys
from os import path

from gratipay import wireup
from gratipay.models.exchange_route import ExchangeRoute
from gratipay.models.participant import Participant


BASE = path.dirname(__file__)


def fake(*a):
    return 'fake-' + sha.new(''.join(map(str, a))).hexdigest()


def _load_stuff(db, user_id, network, address):
    participant = Participant.from_id(user_id)
    route = ExchangeRoute.from_network(participant, network)
    if route is None:
        route = ExchangeRoute.insert(participant, network, address)
    return participant, route


def link(db, log, network, user_id, address, exchange_id, _, __, ref, status):
    participant, route = _load_stuff(db, user_id, network, address)
    SQL = "UPDATE exchanges SET status=%s, route=%s, ref=%s WHERE id=%s"
    db.run(SQL, (status, route.id, ref, exchange_id))
    log(network, participant.username, participant.id, address, exchange_id, _, __, ref, status)


def make(db, log, network, user_id, address, _, timestamp, amount, ref, status):
    participant, route = _load_stuff(db, user_id, network, address)

    SQL = """\

        INSERT INTO exchanges
               ("timestamp", amount, fee, participant, recorder, note, status, route, ref)
        VALUES (%(timestamp)s, %(amount)s, %(fee)s, %(username)s, %(recorder)s, %(note)s,
                %(status)s, %(route)s, %(ref)s)
     RETURNING id

    """

    params = dict( timestamp=timestamp
                 , amount=amount
                 , fee=0
                 , username=participant.username
                 , recorder='Gratipay'
                 , note='https://github.com/gratipay/gratipay.com/pull/3912'
                 , status=status
                 , route=route.id
                 , ref=ref
                  )

    exchange_id = db.one(SQL, params)
    log(network, participant.username, participant.id, address, exchange_id, timestamp, amount,
        ref, status)


def process_row(network, _, user_id, address, exchange_id, timestamp, amount, ref, status):
    assert user_id
    address = address or fake(network, user_id)
    assert status

    if status == 'succeeded':
        if network in ('cash', 'samurai'):
            assert ref == ''
            ref = None
        else:
            assert ref
        func = link
    elif status == 'failed':
        assert ref
        func = make
    else:
        assert 0, locals()

    func(db, log, network, user_id, address, exchange_id, timestamp, amount, ref, status)


def main(db, log):
    for network in os.listdir('backfill'):
        if network.startswith('_'): continue
        data = csv.reader(open(path.join('backfill', network)))
        for row in data:
            process_row(network, *row)


if __name__ == '__main__':
    db = wireup.db(wireup.env())
    writer = csv.writer(sys.stdout)
    log = lambda *a: writer.writerow(a)
    main(db, log)
