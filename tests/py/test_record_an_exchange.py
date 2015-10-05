from __future__ import unicode_literals
from decimal import Decimal

from psycopg2 import IntegrityError
from aspen.utils import utcnow
from gratipay.testing import Harness
from gratipay.models.exchange_route import ExchangeRoute


class TestRecordAnExchange(Harness):

    # fixture
    # =======

    def make_participants(self):
        now = utcnow()
        self.make_participant('alice', claimed_time=now, is_admin=True)
        self.bob = self.make_participant('bob', claimed_time=now)

    def record_an_exchange(self, data, make_participants=True):
        if make_participants:
            self.make_participants()

        data.setdefault('status', 'succeeded')
        data.setdefault('note', 'noted')

        if 'route_id' not in data:
            try:
                data['route_id'] = ExchangeRoute.insert(self.bob, 'paypal', 'bob@gmail.com')
            except IntegrityError:
                data['route_id'] = ExchangeRoute.from_network(self.bob, 'paypal')

        return self.client.PxST('/~bob/history/record-an-exchange', data, auth_as='alice')

    # tests
    # =====

    def test_success_is_302(self):
        actual = self.record_an_exchange({'amount': '10', 'fee': '0'}).code
        assert actual == 302

    def test_non_admin_is_403(self):
        self.make_participant('alice', claimed_time=utcnow())
        self.bob = self.make_participant('bob', claimed_time=utcnow())
        actual = self.record_an_exchange({'amount': '10', 'fee': '0'}, False).code
        assert actual == 403

    def test_bad_amount_is_400(self):
        actual = self.record_an_exchange({'amount': 'cheese', 'fee': '0'}).code
        assert actual == 400

    def test_bad_fee_is_400(self):
        actual = self.record_an_exchange({'amount': '10', 'fee': 'cheese'}).code
        assert actual == 400

    def test_no_note_is_400(self):
        actual = self.record_an_exchange({'amount': '10', 'fee': '0', 'note': ''}).code
        assert actual == 400

    def test_whitespace_note_is_400(self):
        actual = self.record_an_exchange({'amount': '10', 'fee': '0', 'note': '   '}).code
        assert actual == 400

    def test_dropping_balance_below_zero_is_allowed_in_this_context(self):
        self.record_an_exchange({'amount': '-10', 'fee': '0'})
        actual = self.db.one("SELECT balance FROM participants WHERE username='bob'")
        assert actual == Decimal('-10.00')

    def test_success_records_exchange(self):
        self.record_an_exchange({'amount': '10', 'fee': '0.50'})
        expected = { "amount": Decimal('10.00')
                   , "fee": Decimal('0.50')
                   , "participant": "bob"
                   , "recorder": "alice"
                   , "note": "noted"
                    }
        SQL = "SELECT amount, fee, participant, recorder, note " \
              "FROM exchanges"
        actual = self.db.one(SQL, back_as=dict)
        assert actual == expected

    def test_success_updates_balance(self):
        self.record_an_exchange({'amount': '10', 'fee': '0'})
        expected = Decimal('10.00')
        SQL = "SELECT balance FROM participants WHERE username='bob'"
        actual = self.db.one(SQL)
        assert actual == expected

    def test_withdrawals_work(self):
        self.make_participant('alice', claimed_time=utcnow(), is_admin=True)
        self.bob = self.make_participant('bob', claimed_time=utcnow(), balance=20)

        self.record_an_exchange({'amount': '-7', 'fee': '0'}, make_participants=False)

        expected = Decimal('13.00')
        SQL = "SELECT balance FROM participants WHERE username='bob'"
        actual = self.db.one(SQL)
        assert actual == expected

    def test_withdrawals_take_fee_out_of_balance(self):
        self.make_participant('alice', claimed_time=utcnow(), is_admin=True)
        self.bob = self.make_participant('bob', claimed_time=utcnow(), balance=20)
        self.bob = self.record_an_exchange({'amount': '-7', 'fee': '1.13'}, False)
        SQL = "SELECT balance FROM participants WHERE username='bob'"
        assert self.db.one(SQL) == Decimal('11.87')

    def test_can_set_status(self):
        self.make_participants()
        for status in ('pre', 'pending', 'failed', 'succeeded'):
            self.record_an_exchange({'amount': '10', 'fee': '0', 'status': status}, False)
            actual = self.db.one("SELECT status FROM exchanges ORDER BY timestamp desc LIMIT 1")
            assert actual == status

    def test_cant_record_new_exchanges_with_None_status(self):
        r = self.record_an_exchange({'amount': '10', 'fee': '0', 'status': None})
        assert r.code == 400
        assert self.db.one("SELECT count(*) FROM exchanges") == 0

    def test_succeeded_affects_balance(self):
        self.make_participants()
        balance = 0
        for amount in ('10', '-10'):
            self.record_an_exchange({'amount': amount, 'fee': '0'}, False)
            balance += int(amount)
            assert self.db.one("SELECT balance FROM participants WHERE username='bob'") == balance

    def test_failed_doesnt_affect_balance(self):
        self.make_participants()
        for amount in ('10', '-10'):
            self.record_an_exchange({
                'amount': amount,
                'fee': '0',
                'status': 'failed'
            }, False)
            assert self.db.one("SELECT balance FROM participants WHERE username='bob'") == 0

    def test_other_statuses_dont_affect_balance_for_payins(self):
        self.make_participants()
        for status in ('pre', 'pending'):
            self.record_an_exchange({
                'amount': '10',
                'fee': '0',
                'status': status
            }, False)
            assert self.db.one("SELECT balance FROM participants WHERE username='bob'") == 0

    def test_other_statuses_affect_balance_for_payouts(self):
        self.make_participants()
        balance = 0
        for status in ('pre', 'pending'):
            self.record_an_exchange({
                'amount': '-10',
                'fee': '0',
                'status': status
            }, False)
            balance -= 10
            assert self.db.one("SELECT balance FROM participants WHERE username='bob'") == balance
