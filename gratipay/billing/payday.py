"""This is Gratipay's payday algorithm.

Exchanges (moving money between Gratipay and the outside world) and transfers
(moving money amongst Gratipay users) happen within an isolated event called
payday. This event has duration (it's not punctiliar).

Payday is designed to be crash-resistant. Everything that can be rolled back
happens inside a single DB transaction. Exchanges cannot be rolled back, so they
immediately affect the participant's balance.

"""
from __future__ import unicode_literals

import itertools
from multiprocessing.dummy import Pool as ThreadPool

import braintree

import aspen.utils
from aspen import log
from gratipay.billing.exchanges import (
    cancel_card_hold, capture_card_hold, create_card_hold, upcharge, MINIMUM_CHARGE,
)
from gratipay.exceptions import NegativeBalance
from gratipay.models import check_db
from psycopg2 import IntegrityError


with open('sql/payday.sql') as f:
    PAYDAY = f.read()


class ExceptionWrapped(Exception): pass


def threaded_map(func, iterable, threads=5):
    pool = ThreadPool(threads)
    def g(*a, **kw):
        # Without this wrapper we get a traceback from inside multiprocessing.
        try:
            return func(*a, **kw)
        except Exception as e:
            import traceback
            raise ExceptionWrapped(e, traceback.format_exc())
    try:
        r = pool.map(g, iterable)
    except ExceptionWrapped as e:
        print(e.args[1])
        raise e.args[0]
    pool.close()
    pool.join()
    return r


class NoPayday(Exception):
    __str__ = lambda self: "No payday found where one was expected."


class Payday(object):
    """Represent an abstract event during which money is moved.

    On Payday, we want to use a participant's Gratipay balance to settle their
    tips due (pulling in more money via credit card as needed), but we only
    want to use their balance at the start of Payday. Balance changes should be
    atomic globally per-Payday.

    Here's the call structure of the Payday.run method:

        run
            payin
                prepare
                create_card_holds
                process_payment_instructions
                transfer_takes
                process_draws
                settle_card_holds
                update_balances
                take_over_balances
            update_stats
            end

    """


    @classmethod
    def start(cls):
        """Try to start a new Payday.

        If there is a Payday that hasn't finished yet, then the UNIQUE
        constraint on ts_end will kick in and notify us of that. In that case
        we load the existing Payday and work on it some more. We use the start
        time of the current Payday to synchronize our work.

        """
        try:
            d = cls.db.one("""
                INSERT INTO paydays DEFAULT VALUES
                RETURNING id, (ts_start AT TIME ZONE 'UTC') AS ts_start, stage
            """, back_as=dict)
            log("Starting a new payday.")
        except IntegrityError:  # Collision, we have a Payday already.
            d = cls.db.one("""
                SELECT id, (ts_start AT TIME ZONE 'UTC') AS ts_start, stage
                  FROM paydays
                 WHERE ts_end='1970-01-01T00:00:00+00'::timestamptz
            """, back_as=dict)
            log("Picking up with an existing payday.")

        d['ts_start'] = d['ts_start'].replace(tzinfo=aspen.utils.utc)

        log("Payday started at %s." % d['ts_start'])

        payday = Payday()
        payday.__dict__.update(d)
        return payday


    def run(self):
        """This is the starting point for payday.

        This method runs every Thursday. It is structured such that it can be
        run again safely (with a newly-instantiated Payday object) if it
        crashes.

        """
        self.db.self_check()

        _start = aspen.utils.utcnow()
        log("Greetings, program! It's PAYDAY!!!!")

        if self.stage < 1:
            self.payin()
            self.mark_stage_done()
        if self.stage < 2:
            self.update_stats()
            self.mark_stage_done()

        self.end()
        self.notify_participants()

        _end = aspen.utils.utcnow()
        _delta = _end - _start
        fmt_past = "Script ran for %%(age)s (%s)." % _delta
        log(aspen.utils.to_age(_start, fmt_past=fmt_past))


    def payin(self):
        """The first stage of payday where we charge credit cards and transfer
        money internally between participants.
        """
        with self.db.get_cursor() as cursor:
            self.prepare(cursor, self.ts_start)
            holds = self.create_card_holds(cursor)
            self.process_payment_instructions(cursor)
            self.transfer_takes(cursor, self.ts_start)
            self.process_draws(cursor)
            payments = cursor.all("""
                SELECT * FROM payments WHERE "timestamp" > %s
            """, (self.ts_start,))
            try:
                self.settle_card_holds(cursor, holds)
                self.update_balances(cursor)
                check_db(cursor)
            except:
                # Dump payments for debugging
                import csv
                from time import time
                with open('%s_payments.csv' % time(), 'wb') as f:
                    csv.writer(f).writerows(payments)
                raise
        self.take_over_balances()


    @staticmethod
    def prepare(cursor, ts_start):
        """Prepare the DB: we need temporary tables with indexes and triggers.
        """
        cursor.run(PAYDAY, dict(ts_start=ts_start))
        log('Prepared the DB.')


    @staticmethod
    def fetch_card_holds(participant_ids):
        log('Fetching card holds.')
        holds = {}
        existing_holds = braintree.Transaction.search(
            braintree.TransactionSearch.status == 'authorized'
        )
        for hold in existing_holds.items:
            log_amount = hold.amount
            p_id = int(hold.custom_fields['participant_id'])
            if p_id in participant_ids:
                log('Reusing a ${:.2f} hold for {}.'.format(log_amount, p_id))
                holds[p_id] = hold
            else:
                cancel_card_hold(hold)
        return holds


    def create_card_holds(self, cursor):

        # Get the list of participants to create card holds for
        participants = cursor.all("""
            SELECT *
              FROM payday_participants
             WHERE old_balance < giving_today
               AND has_credit_card
               AND is_suspicious IS false
        """)
        if not participants:
            return {}

        # Fetch existing holds
        participant_ids = set(p.id for p in participants)
        holds = self.fetch_card_holds(participant_ids)

        # Create new holds and check amounts of existing ones
        def f(p):
            amount = p.giving_today
            if p.old_balance < 0:
                amount -= p.old_balance
            if p.id in holds:
                if amount >= MINIMUM_CHARGE:
                    charge_amount = upcharge(amount)[0]
                    if holds[p.id].amount >= charge_amount:
                        return
                    else:
                        # The amount is too low, cancel the hold and make a new one
                        cancel_card_hold(holds.pop(p.id))
                else:
                    # not up to minimum charge level. cancel the hold
                    cancel_card_hold(holds.pop(p.id))
                    return
            if amount >= MINIMUM_CHARGE:
                hold, error = create_card_hold(self.db, p, amount)
                if error:
                    return 1
                else:
                    holds[p.id] = hold
        threaded_map(f, participants)

        # Update the values of card_hold_ok in our temporary table
        if not holds:
            return {}
        cursor.run("""
            UPDATE payday_participants p
               SET card_hold_ok = true
             WHERE p.id IN %s
        """, (tuple(holds.keys()),))

        return holds


    @staticmethod
    def process_payment_instructions(cursor):
        """Trigger the process_payment_instructions function for each row in
        payday_payment_instructions.
        """
        log("Processing payment instructions.")
        cursor.run("UPDATE payday_payment_instructions SET is_funded=true;")


    @staticmethod
    def transfer_takes(cursor, ts_start):
        return  # XXX Bring me back!
        cursor.run("""

        INSERT INTO payday_takes
            SELECT team, member, amount
              FROM ( SELECT DISTINCT ON (team, member)
                            team, member, amount, ctime
                       FROM takes
                      WHERE mtime < %(ts_start)s
                   ORDER BY team, member, mtime DESC
                   ) t
             WHERE t.amount > 0
               AND t.team IN (SELECT username FROM payday_participants)
               AND t.member IN (SELECT username FROM payday_participants)
               AND ( SELECT id
                       FROM payday_transfers_done t2
                      WHERE t.team = t2.tipper
                        AND t.member = t2.tippee
                        AND context = 'take'
                   ) IS NULL
          ORDER BY t.team, t.ctime DESC;

        """, dict(ts_start=ts_start))


    @staticmethod
    def process_draws(cursor):
        """Send whatever remains after payroll to the team owner.
        """
        log("Processing draws.")
        cursor.run("UPDATE payday_teams SET is_drained=true;")


    def settle_card_holds(self, cursor, holds):
        log("Settling card holds.")
        participants = cursor.all("""
            SELECT *
              FROM payday_participants
             WHERE new_balance < 0
        """)
        participants = [p for p in participants if p.id in holds]

        log("Capturing card holds.")
        # Capture holds to bring balances back up to (at least) zero
        def capture(p):
            amount = -p.new_balance
            capture_card_hold(self.db, p, amount, holds.pop(p.id))
        threaded_map(capture, participants)
        log("Captured %i card holds." % len(participants))

        log("Canceling card holds.")
        # Cancel the remaining holds
        threaded_map(cancel_card_hold, holds.values())
        log("Canceled %i card holds." % len(holds))


    @staticmethod
    def update_balances(cursor):
        log("Updating balances.")
        participants = cursor.all("""

            UPDATE participants p
               SET balance = (balance + p2.new_balance - p2.old_balance)
              FROM payday_participants p2
             WHERE p.id = p2.id
               AND p2.new_balance <> p2.old_balance
         RETURNING p.id
                 , p.username
                 , balance AS new_balance
                 , ( SELECT balance
                       FROM participants p3
                      WHERE p3.id = p.id
                   ) AS cur_balance;

        """)
        # Check that balances aren't becoming (more) negative
        for p in participants:
            if p.new_balance < 0 and p.new_balance < p.cur_balance:
                log(p)
                raise NegativeBalance()
        cursor.run("""
            INSERT INTO payments (timestamp, participant, team, amount, direction, payday)
                SELECT *, (SELECT id FROM paydays WHERE extract(year from ts_end) = 1970)
                  FROM payday_payments;
        """)
        # Copy due value back to payment_instructions
        cursor.run("""
            UPDATE payment_instructions pi
               SET due = pi2.due
              FROM payment_instructions_due pi2
             WHERE pi.id = pi2.id
        """)
        # Reset older due values to zero
        cursor.run("""
            UPDATE payment_instructions pi
               SET due = '0'
             WHERE pi.id NOT IN (
                 SELECT id
                   FROM payment_instructions_due pi2)
        """)

        log("Updated the balances of %i participants." % len(participants))


    def take_over_balances(self):
        """If an account that receives money is taken over during payin we need
        to transfer the balance to the absorbing account.
        """
        log("Taking over balances.")
        for i in itertools.count():
            if i > 10:
                raise Exception('possible infinite loop')
            count = self.db.one("""

                DROP TABLE IF EXISTS temp;
                CREATE TEMPORARY TABLE temp AS
                    SELECT archived_as, absorbed_by, balance AS archived_balance
                      FROM absorptions a
                      JOIN participants p ON a.archived_as = p.username
                     WHERE balance > 0;

                SELECT count(*) FROM temp;

            """)
            if not count:
                break
            self.db.run("""

                INSERT INTO transfers (tipper, tippee, amount, context)
                    SELECT archived_as, absorbed_by, archived_balance, 'take-over'
                      FROM temp;

                UPDATE participants
                   SET balance = (balance - archived_balance)
                  FROM temp
                 WHERE username = archived_as;

                UPDATE participants
                   SET balance = (balance + archived_balance)
                  FROM temp
                 WHERE username = absorbed_by;

            """)


    def update_stats(self):
        log("Updating stats.")
        self.db.run("""\

            WITH our_payments AS (SELECT * FROM payments WHERE payday=%(payday)s)
            UPDATE paydays p
               SET nusers = (SELECT count(*) FROM (
                    SELECT DISTINCT ON (participant) participant FROM our_payments GROUP BY participant
                   ) AS foo)
                 , nteams = (SELECT count(*) FROM (
                    SELECT DISTINCT ON (team) team FROM our_payments GROUP BY team
                   ) AS foo)
                 , volume = (
                    SELECT COALESCE(sum(amount), 0)
                      FROM our_payments
                     WHERE payday=p.id AND direction='to-team'
                   )
             WHERE id=%(payday)s

        """, {'payday': self.id})
        log("Updated payday stats.")


    def end(self):
        self.ts_end = self.db.one("""\

            UPDATE paydays
               SET ts_end=now()
             WHERE ts_end='1970-01-01T00:00:00+00'::timestamptz
         RETURNING ts_end AT TIME ZONE 'UTC'

        """, default=NoPayday).replace(tzinfo=aspen.utils.utc)


    def notify_participants(self):
        log("Notifying participants.")
        ts_start, ts_end = self.ts_start, self.ts_end
        exchanges = self.db.all("""
            SELECT e.id, amount, fee, note, status, p.*::participants AS participant
              FROM exchanges e
              JOIN participants p ON e.participant = p.username
             WHERE "timestamp" >= %(ts_start)s
               AND "timestamp" < %(ts_end)s
               AND amount > 0
               AND p.notify_charge > 0
        """, locals())
        for e in exchanges:
            if e.status not in ('failed', 'succeeded'):
                log('exchange %s has an unexpected status: %s' % (e.id, e.status))
                continue
            i = 1 if e.status == 'failed' else 2
            p = e.participant
            if p.notify_charge & i == 0:
                continue
            username = p.username
            nteams, top_team = self.db.one("""
                WITH tippees AS (
                         SELECT t.slug, amount
                           FROM ( SELECT DISTINCT ON (team) team, amount
                                    FROM payment_instructions
                                   WHERE mtime < %(ts_start)s
                                     AND participant = %(username)s
                                ORDER BY team, mtime DESC
                                ) s
                           JOIN teams t ON s.team = t.slug
                           JOIN participants p ON t.owner = p.username
                          WHERE s.amount > 0
                            AND t.is_approved IS true
                            AND t.is_closed IS NOT true
                            AND (SELECT count(*)
                                   FROM current_exchange_routes er
                                  WHERE er.participant = p.id
                                    AND network = 'paypal'
                                    AND error = ''
                                ) > 0
                     )
                SELECT ( SELECT count(*) FROM tippees ) AS nteams
                     , ( SELECT slug
                           FROM tippees
                       ORDER BY amount DESC
                          LIMIT 1
                       ) AS top_team
            """, locals())
            p.queue_email(
                'charge_'+e.status,
                exchange=dict(id=e.id, amount=e.amount, fee=e.fee, note=e.note),
                nteams=nteams,
                top_team=top_team,
            )


    def mark_stage_done(self):
        self.db.one("""\

            UPDATE paydays
               SET stage = stage + 1
             WHERE ts_end='1970-01-01T00:00:00+00'::timestamptz
         RETURNING id

        """, default=NoPayday)
