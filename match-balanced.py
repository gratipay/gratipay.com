#!/usr/bin/env python2 -u
from __future__ import absolute_import, division, print_function, unicode_literals

import csv
import datetime
import os
import time
from collections import defaultdict
from decimal import Decimal as D

import psycopg2.tz
from gratipay import wireup


header = lambda h: print(h.upper() + ' ' + ((80 - len(h) - 1) * '-'))


class Heck(Exception): pass
SIXTY_SECONDS = datetime.timedelta(seconds=60)


def datetime_from_iso(iso):
    date, time_ = iso.split('T')
    assert time_[-1] == 'Z'
    time_ = time_[:-1]
    year, month, day = map(int, date.split('-'))
    hour, minute, second_microsecond = time_.split(':')
    hour, minute = map(int, (hour, minute))
    second, microsecond = map(int, second_microsecond.split('.'))
    tz = psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)
    return datetime.datetime(year, month, day, hour, minute, second, microsecond, tzinfo=tz)


def usernames_match(transaction, exchange):
    if not exchange.participant: import pdb; pdb.set_trace()
    return transaction['description'] == exchange.participant


def amounts_match(transaction, exchange):
    amount = transaction['amount']
    if (exchange.amount > 0) and (exchange.amount + exchange.fee != amount):
        return False
    if (exchange.amount < 0) and (exchange.amount != amount):
        return False
    return True


def ts_within(transaction, exchange, seconds):
    ts_transaction = transaction['timestamp']
    ts_exchange = exchange.timestamp
    limit = ts_transaction + datetime.timedelta(seconds=seconds)
    return ts_exchange <= limit


def get_exchanges(db):
    return db.all("""\

            SELECT e.*, p.id as user_id, r.network as network
              FROM exchanges e
              JOIN participants p
                ON e.participant = p.username
   LEFT OUTER JOIN exchange_routes r
                ON e.route = r.id
             WHERE recorder IS NULL -- filter out PayPal
          ORDER BY "timestamp" asc

    """)


def get_transactions(root):
    transactions = []
    card2usernames = defaultdict(set)
    username2cids = defaultdict(set)

    for dirpath, dirnames, filenames in os.walk(root):
        for filename in filenames:
            if filename != '_balanced.csv':
                continue
            fp = open(os.path.join(dirpath, filename))
            reader = csv.reader(fp)
            headers = reader.next()

            for row in reader:
                rec = dict(zip(headers, row))
                username = rec['description']
                cid = rec['links__customer']

                # special-case the first test transactions
                if rec['id'] in ('WD7qFYL9rqIrCUmbXsgJJ8HT', 'WD16Zqy9ISWN5muEhXo19vpn'):
                    continue

                # special-case escrow shuffles to/from Gratipay
                if cid == 'AC13kr5rmbUkMJWbocmNs3tD':
                    continue

                # convert cents to decimal dollars
                rec['amount'] = '{}.{}'.format(rec['amount'][:-2], rec['amount'][-2:])
                if rec['amount'].startswith('.'):
                    rec['amount'] = '0' + rec['amount']
                rec['amount'] = D(rec['amount'])

                # convert created_at to timestamp
                rec['timestamp'] = datetime_from_iso(rec['created_at'])

                # check status
                if not rec['status'] in ('succeeded', 'failed'):
                    raise Exception(rec)

                # check kind
                if rec['kind'] == 'card_hold':
                    if rec['links__debit']:

                        # Balanced has one or two transactions, card_hold and
                        # possibly debit, where we only have one exchange. We
                        # can skip card_holds where there are debits.

                        continue
                    else:

                        # If we are gonna run with a card_hold, we need to jump
                        # through hoops to be able to deference a cid from it
                        # later on.

                        card = rec['links__card']
                        if not card or not username:
                            import pdb; pdb.set_trace()
                        card2usernames[card].add(username)

                elif rec['kind'] in ('credit', 'refund'):
                    rec['amount'] = -rec['amount']
                elif rec['kind'] in ('debit', 'reversal'):
                    pass
                else:
                    raise Exception(rec)

                # Map cid to usernames--more hoop-jumping
                if username and cid:
                    username2cids[username].add(cid)

                transactions.append(rec)

    # may not be necessary, but just to be sure ...
    transactions.sort(key=lambda rec: rec['created_at'])

    return transactions, card2usernames, username2cids


class Matcher(object):

    def __init__(self, db, root):
        print("Loading transactions ... ", end='')
        self.transactions, card2usernames, username2cids = get_transactions(root)
        print("we have {} transactions to match!".format(len(self.transactions)))

        print("Loading exchanges ... ", end='')
        self.exchanges = get_exchanges(db)
        print("we have {} exchanges to match!".format(len(self.exchanges)))

        self.unmatchable = defaultdict(list)


        # Do goofiness to map cid to transactions

        card2cid = {}
        for t in self.transactions:
            cid, card = t['links__customer'], t['links__card']
            if cid == '':
                continue
            card2cid[card] = cid

        self.cid2transactions = defaultdict(list)
        for t in self.transactions:
            cid = t['links__customer']

            if t['status'] == 'failed' and t['created_at'] < '2014-12-18':
                # We didn't record failures before this date.
                self.unmatchable['early_failures'].append(t)
                continue

            if not cid:
                # It seems that card holds don't have a customer link.
                if t['kind'] != 'card_hold':
                    self.unmatchable['non_card_hold_without_cid'].append(t)
                    continue
                if t['links__debit'] != '':
                    # Though if the card hold is linked to a debit, then we'll pass here
                    # and just work with the debit (when we get to it) instead.
                    continue
                if not t['links__card']:
                    # Okay: but the card hold *should* have a card.
                    self.unmatchable['card_hold_without_card'].append(t)
                    continue

                # Can we unambiguously determine a cid from the card?
                usernames = card2usernames[t['links__card']]
                cids = set.union(*[username2cids[username] for username in usernames])
                if len(cids) != 1:
                    self.unmatchable['ambiguous_card_hold'].append(t)
                    continue
                cid = tuple(cids)[0]

            if not cid:
                self.unmatchable['still_no_cid'].append(t)
                continue

            self.cid2transactions[cid].append(t)

        # A little less goofiness to map uid to exchanges
        self.uid2exchanges = defaultdict(list)
        for e in self.exchanges:
            self.uid2exchanges[e.user_id].append(e)

        self.matches = []


    def inner_loop(self, cid, uid):

        transactions = self.cid2transactions[cid]
        exchanges = self.uid2exchanges[uid]


        # Remove from global lists
        # ========================
        # also decrement global indices if the transaction or exchange's
        # timestamp is less than the one that landed us here

        for transaction in transactions:
            if transaction['timestamp'] < self.transactions[self.I]['timestamp']:
                self.I -= 1
            self.transactions.remove(transaction)

        for exchange in exchanges:
            if exchange.timestamp < self.exchanges[self.J].timestamp:
                self.J -= 1
                self.K -= 1
            self.exchanges.remove(exchange)


        # Match items in the local lists if we can.
        # =========================================

        matched_t = set()
        matched_e = set()

        for t in transactions:
            if t['id'] in matched_t: continue
            timelimit = t['timestamp'] - SIXTY_SECONDS
            i = 0
            while i < len(exchanges):
                e = exchanges[i]
                assert not e.id in matched_e

                # Fast-forward to an exchange that is within a certain time
                # tolerance of the current transaction.
                if e.timestamp < timelimit or not ts_within(t, e, 6*3600):
                    i += 1
                    continue

                # See if the amounts match.
                if not amounts_match(t, e):

                    # We appear to have recorded the nominal amount of the tip
                    # for failed exchanges, not the charge amount. I guess
                    # let's link these on the strength of the cid/uid and
                    # timestamp match?

                    if t['status'] == 'failed':
                        if e.amount > t['amount']:
                            self.unmatchable['exchanges.bad-amount-failed'].append(e)
                            exchanges.remove(e)
                            continue
                    else:
                        self.unmatchable['exchanges.bad-amount-succeeded'].append(e)
                        exchanges.remove(e)
                        continue

                exchanges.remove(e)
                matched_t.add(t['id'])
                matched_e.add(e.id)
                self.matches.append((t, e))

                if 0:
                    if e.network not in ('balanced-cc', 'balanced-ba', None):
                        self.unmatchable['exchanges.bad-network'].append(e)
                        exchanges.remove(e)
                        continue
                    # XXX Bring me back!
                    if e.ref is None and e.status is None:
                        print('missing ref and status!')
                    elif e.ref != t['id'] and e.status != t['status']:
                        print('mismatched ref and status!')
                    elif e.ref is None:
                        print('missing ref!')
                    elif e.ref != t['id']:
                        print('mismatched ref!')
                    elif e.status is None:
                        print('missing status!')
                    elif e.status != t['status']:
                        print('mismatched status!')

                break

        self.unmatchable['dregs'] += [t for t in transactions if t['id'] not in matched_t]
        self.unmatchable['exchanges'] += [e for e in exchanges if e.id not in matched_e]


    def main(self):
        """Remove matches from _exchanges and _transactions and return a list of
        (exchange, transaction) match tuples
        """
        h = done = self.I = self.J = self.K = 0
        start = time.time()
        N_initial = len(self.transactions)
        while not done:

            # output a progress report
            h += 1
            if h % 10 == 0:
                N = len(self.transactions)
                M = len(self.exchanges)
                perc = (N_initial - N) / N_initial

                elapsed = time.time() - start
                total = elapsed / (perc or 0.001)
                remaining = total - elapsed

                if remaining > 24*60*60:
                    remaining = '{:.1f} d'.format(remaining / 60 / 60 / 24)
                elif remaining > 60*60:
                    remaining = '{:.1f} h'.format(remaining / 60 / 60)
                elif remaining > 60:
                    remaining = '{:.1f} m'.format(remaining / 60)
                else:
                    remaining = '{} s'.format(int(remaining))

                print('\r{:>5} / {:>5} | {:>5} / {:>5} | {} matches | {:4.1f}% | T-{:<20}'
                      .format( self.I, N
                             , self.J, M
                             , len(self.matches)
                             , perc * 100
                             , remaining
                              ), end='')

            # Grab the next transaction and exchange.
            transaction = self.transactions[self.I]
            exchange = self.exchanges[self.J]

            # See if the two match.
            if amounts_match(transaction, exchange) and usernames_match(transaction, exchange):
                cid = transaction['links__customer']
                uid = exchange.user_id
                self.inner_loop(cid, uid)
                self.K = self.J
                continue

            # Advance the outer loop.
            done = self.advance()


    def advance(self):
        """Return bool (whether to continue the outer loop).
        """

        try:            # try incrementing J
            I = self.I
            J = self.J + 1

            # Check for the end of the list.
            if J == len(self.exchanges):
                raise Heck

            # Check for 10+ seconds beyond the transaction.
            if not ts_within(self.transactions[I], self.exchanges[J], 10):
                raise Heck

        except Heck:    # increment I instead

            I = self.I + 1
            J = self.K

            # Check for the end of the list.
            if I == len(self.transactions):
                return True

            # Reset J.
            transaction = self.transactions[I]
            while not ts_within(transaction, self.exchanges[J], 0):
                J -= 1

        self.I = I
        self.J = J
        return False


    def dump(self):
        out = csv.writer(open('balanced', 'w+'))
        for transaction, exchange in self.matches:
            out.writerow(( exchange.participant
                         , exchange.user_id
                         , transaction['links__customer']
                         , exchange.id
                         , exchange.amount
                         , transaction['id']
                         , transaction['status']
                         , transaction['kind']
                          ))

        for reason in self.unmatchable:
            out = csv.writer(open('unmatchable.{}'.format(reason), 'w+'))
            is_exchanges = lambda r: r.startswith('exchanges')
            flatten = lambda o: o._asdict().items() if is_exchanges(reason) else sorted(o.items())
            for rec in self.unmatchable[reason]:
                out.writerow([kv[1] for kv in flatten(rec)])


if __name__ == '__main__':
    _db = wireup.db(wireup.env())
    _root = os.path.abspath('3912')
    matcher = Matcher(_db, _root)

    try:
        matcher.main()
    except:
        ask_before_dumping = True
    else:
        ask_before_dumping = False

    print("\nWe found {} matches!".format(len(matcher.matches)))
    if ask_before_dumping:
        if raw_input("Dump data so far? (y/N) ") == 'y':
            matcher.dump()
    else:
        matcher.dump()


"""
Fields in balanced.csv:

    id
    kind
    meta_state
    meta_participant_id
    transaction_number
    status
    created_at
    updated_at
    failure_reason_code
    currency
    voided_at
    href
    amount
    description
    expires_at
    failure_reason
    meta_exchange_id
    appears_on_statement_as
    meta_balanced.result.trace_number
    meta_balanced.result.return_reason_code

"""
