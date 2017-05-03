from __future__ import absolute_import, division, print_function, unicode_literals

from datetime import datetime
import json

from mock import patch

from gratipay.billing.payday import Payday
from gratipay.models.participant import Participant
from gratipay.testing import Harness, D,P
from gratipay.testing.billing import BillingHarness
from gratipay.utils.history import get_end_of_year_balance, iter_payday_events


def make_history(harness):
    alice = harness.make_participant('alice', claimed_time=datetime(2001, 1, 1))

    # Exchanges for the previous year
    harness.make_exchange('braintree-cc', 60, 0, alice)
    harness.make_exchange('braintree-cc', 12, 0, alice, status='failed')
    harness.make_exchange('paypal', -40, 0, alice)
    harness.make_exchange('paypal', -5, 0, alice, status='failed')
    past_year = harness.db.all("""
        UPDATE exchanges
           SET timestamp = "timestamp" - interval '1 year'
     RETURNING extract(year from timestamp)::int
    """)[0]

    # Exchanges for the current year
    harness.make_exchange('braintree-cc', 45, 0, alice)
    harness.make_exchange('braintree-cc', 49, 0, alice, status='failed')
    harness.make_exchange('paypal', -15, 0, alice)
    harness.make_exchange('paypal', -7, 0, alice, status='failed')

    # Tips under Gratipay 1.0
    harness.make_participant('bob')
    tips = [
        {'timestamp': datetime(past_year, 1, 1), 'amount': 10},
        {'timestamp': datetime(past_year+1, 1, 1), 'amount': 20}
    ]
    for tip in tips:
        harness.db.run("""
            INSERT INTO transfers (tipper, tippee, amount, context, timestamp)
                 VALUES ('alice', 'bob', %(amount)s, 'tip', %(timestamp)s);

                 UPDATE participants
                    SET balance = (balance - %(amount)s)
                  WHERE username = 'alice';

                 UPDATE participants
                    SET balance = (balance + %(amount)s)
                  WHERE username = 'bob';
        """, tip)

    harness.alice = Participant.from_username('alice')
    harness.past_year = past_year


class TestHistory(BillingHarness):

    def shift_all_paydays_by(self, interval):
        self.db.run("""
            UPDATE paydays
               SET ts_start = ts_start + interval %(interval)s;
            UPDATE paydays
               SET ts_end = ts_end + interval %(interval)s
             WHERE NOT ts_end::text = '1970-01-01 00:00:00+00';
            UPDATE payments
               SET timestamp = "timestamp" + interval %(interval)s;
            UPDATE exchanges
               SET timestamp = "timestamp" + interval %(interval)s;
            UPDATE transfers
               SET timestamp = "timestamp" + interval %(interval)s;
        """, dict(interval=interval))

    def test_iter_payday_events(self):
        now = datetime.now()
        self.run_payday()
        self.shift_all_paydays_by('-1 week')

        Enterprise = self.make_team(is_approved=True)
        self.obama.set_payment_instruction(Enterprise, '10.00')  # >= MINIMUM_CHARGE!
        for i in range(2):
            with patch.object(Payday, 'fetch_card_holds') as fch:
                fch.return_value = {}
                self.run_payday()
            self.shift_all_paydays_by('-1 week')

        obama = P('obama')
        picard = P('picard')

        assert obama.balance == D('0.00')
        assert picard.balance == D('20.00')

        self.start_payday()  # to demonstrate that we ignore any open payday?

        # Make all events in the same year.
        if now.month < 2:

            # Above, we created four paydays in sequential weeks, with the
            # latest being today. We don't want them to go back into the
            # previous year, so let's shift them forward if it's close.

            self.shift_all_paydays_by('3 months')

        events = list(iter_payday_events(self.db, picard, now.year))
        assert len(events) == 7
        assert events[0]['kind'] == 'totals'
        assert events[0]['given'] == 0
        assert events[0]['received'] == 20
        assert events[1]['kind'] == 'day-open'
        assert events[1]['payday_number'] == 2
        assert events[2]['balance'] == 20
        assert events[-1]['kind'] == 'day-close'
        assert events[-1]['balance'] == 0

        events = list(iter_payday_events(self.db, obama))
        assert events[0]['given'] == 20
        assert len(events) == 9

    def test_iter_payday_events_with_failed_exchanges(self):
        alice = self.make_participant('alice', claimed_time='now')
        self.make_exchange('braintree-cc', 50, 0, alice)
        self.make_exchange('braintree-cc', 12, 0, alice, status='failed')
        self.make_exchange('paypal', -40, 0, alice, status='failed')
        events = list(iter_payday_events(self.db, alice))
        assert len(events) == 5
        assert events[0]['kind'] == 'day-open'
        assert events[0]['balance'] == 50
        assert events[1]['kind'] == 'credit'
        assert events[1]['balance'] == 50
        assert events[2]['kind'] == 'charge'
        assert events[2]['balance'] == 50
        assert events[3]['kind'] == 'charge'
        assert events[3]['balance'] == 50
        assert events[4]['kind'] == 'day-close'
        assert events[4]['balance'] == 0

    def test_get_end_of_year_balance(self):
        make_history(self)

        past_year, current_year = self.past_year, self.past_year+1

        balance = get_end_of_year_balance(self.db, self.alice, past_year, current_year)
        assert balance == 10 # 0 (previous), +60 (payin), -40 (payout), -10 (bob)

        balance = get_end_of_year_balance(self.db, self.alice, current_year, current_year)
        assert balance == 20 # 10 (previous), +45 (payin), -15 (payout), -20 (bob)


class TestHistoryPage(Harness):

    def setUp(self):
        Harness.setUp(self)
        make_history(self)

    def test_participant_can_view_history(self):
        assert self.client.GET('/~alice/history/', auth_as='alice').code == 200

    def test_admin_can_view_closed_participant_history(self):
        self.make_exchange('paypal', -20, 0, self.alice)
        self.alice.close()

        self.make_participant('carl', claimed_time='now', is_admin=True)
        response = self.client.GET('/~alice/history/?year=%s' % self.past_year, auth_as='carl')
        assert "automatic charge" in response.body

class TestExport(Harness):

    def setUp(self):
        Harness.setUp(self)
        make_history(self)

    def test_export_json(self):
        r = self.client.GET('/~alice/history/export.json', auth_as='alice')

        expected = {
            'given': [{'amount': 20, 'tippee': 'bob'}],
            'taken': []
        }
        actual = json.loads(r.body)
        assert expected == actual

    def test_export_json_for_year(self):
        r = self.client.GET('/~alice/history/export.json?year=%s' % (self.past_year), auth_as='alice')
        expected = {
            'given': [{'amount': 10, 'tippee': 'bob'}],
            'taken': []
        }
        actual = json.loads(r.body)
        assert expected == actual

    def test_export_csv(self):
        r = self.client.GET('/~alice/history/export.csv?key=given', auth_as='alice')

        assert r.body.count('\n') == 2 # Tip to bob, Ending newline
