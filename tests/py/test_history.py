from __future__ import absolute_import, division, print_function, unicode_literals

from datetime import datetime
from decimal import Decimal as D
import json
import time

from mock import patch

from gratipay.billing.payday import Payday
from gratipay.models.participant import Participant
from gratipay.testing import Harness
from gratipay.testing.billing import BillingHarness
from gratipay.utils.history import get_end_of_year_balance, iter_payday_events


def make_history(harness):
    alice = harness.make_participant('alice', claimed_time=datetime(2001, 1, 1, 0, 0, 0))
    harness.alice = alice
    harness.make_exchange('braintree-cc', 50, 0, alice)
    harness.make_exchange('braintree-cc', 12, 0, alice, status='failed')
    harness.make_exchange('paypal', -40, 0, alice)
    harness.make_exchange('paypal', -5, 0, alice, status='failed')
    harness.db.run("""
        UPDATE exchanges
           SET timestamp = "timestamp" - interval '1 year'
    """)
    harness.past_year = int(harness.db.one("""
        SELECT extract(year from timestamp)
          FROM exchanges
      ORDER BY timestamp ASC
         LIMIT 1
    """))
    harness.make_exchange('braintree-cc', 35, 0, alice)
    harness.make_exchange('braintree-cc', 49, 0, alice, status='failed')
    harness.make_exchange('paypal', -15, 0, alice)
    harness.make_exchange('paypal', -7, 0, alice, status='failed')


class TestHistory(BillingHarness):

    def test_iter_payday_events(self):
        Payday().start().run()

        Enterprise = self.make_team(is_approved=True)
        self.obama.set_payment_instruction(Enterprise, '10.00')  # >= MINIMUM_CHARGE!
        for i in range(2):
            with patch.object(Payday, 'fetch_card_holds') as fch:
                fch.return_value = {}
                Payday.start().run()
            self.db.run("""
                UPDATE paydays
                   SET ts_start = ts_start - interval '1 week'
                     , ts_end = ts_end - interval '1 week';
                UPDATE payments
                   SET timestamp = "timestamp" - interval '1 week';
                UPDATE transfers
                   SET timestamp = "timestamp" - interval '1 week';
            """)


        obama = Participant.from_username('obama')
        picard = Participant.from_username('picard')

        assert obama.balance == D('0.00')
        assert picard.balance == D('20.00')

        Payday().start()  # to demonstrate that we ignore any open payday?

        events = list(iter_payday_events(self.db, picard))
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
        assert len(events) == 11

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
        balance = get_end_of_year_balance(self.db, self.alice, self.past_year, datetime.now().year)
        assert balance == 10


class TestHistoryPage(Harness):

    def setUp(self):
        Harness.setUp(self)
        make_history(self)

    def test_participant_can_view_history(self):
        assert self.client.GET('/~alice/history/', auth_as='alice').code == 200

    def test_admin_can_view_closed_participant_history(self):
        self.make_exchange('braintree-cc', -30, 0, self.alice)
        self.alice.close()

        self.make_participant('bob', claimed_time='now', is_admin=True)
        response = self.client.GET('/~alice/history/?year=%s' % self.past_year, auth_as='bob')
        assert "automatic charge" in response.body

class TestExport(Harness):

    def setUp(self):
        Harness.setUp(self)
        make_history(self)

    def test_export_json(self):
        r = self.client.GET('/~alice/history/export.json', auth_as='alice')
        assert json.loads(r.body)

    def test_export_json_aggregate(self):
        r = self.client.GET('/~alice/history/export.json?mode=aggregate', auth_as='alice')
        assert json.loads(r.body)

    def test_export_json_past_year(self):
        r = self.client.GET('/~alice/history/export.json?year=%s' % self.past_year, auth_as='alice')
        assert len(json.loads(r.body)['exchanges']) == 4

    def test_export_csv(self):
        r = self.client.GET('/~alice/history/export.csv?key=exchanges', auth_as='alice')
        assert r.body.count('\n') == 5
