from __future__ import absolute_import, division, print_function, unicode_literals

import braintree
from braintree.test.nonces import Nonces
import mock
import pytest

from aspen.utils import typecheck
from gratipay.billing.exchanges import (
    _prep_hit,
    cancel_card_hold,
    capture_card_hold,
    create_card_hold,
    record_exchange,
    record_exchange_result,
    get_ready_payout_routes_by_network
)
from gratipay.exceptions import NegativeBalance, NotWhitelisted
from gratipay.models.exchange_route import ExchangeRoute
from gratipay.testing import Foobar, Harness, D,P
from gratipay.testing.billing import BillingHarness


class TestsWithBillingHarness(BillingHarness):

    def setUp(self):
        super(TestsWithBillingHarness, self).setUp()
        self.hold = None

    def tearDown(self):
        if self.hold:
            cancel_card_hold(self.hold)
        super(TestsWithBillingHarness, self).tearDown()


    # cch - create_card_hold

    def test_cch_success(self):
        self.hold, error = create_card_hold(self.db, self.obama, D('1.00'))
        assert isinstance(self.hold, braintree.Transaction)
        assert self.hold.status == 'authorized'
        assert self.hold.amount == D('10.00')
        assert error == ''
        assert self.obama.balance == P('obama').balance == 0

    def test_cch_for_suspicious_raises_NotWhitelisted(self):
        bob = self.make_participant('bob', is_suspicious=True,
                                    balanced_customer_href='fake_href')
        with self.assertRaises(NotWhitelisted):
            create_card_hold(self.db, bob, D('1.00'))

    @mock.patch('braintree.Transaction.sale')
    def test_cch_failure(self, btsale):
        btsale.side_effect = Foobar
        self.hold, error = create_card_hold(self.db, self.obama, D('1.00'))
        assert self.hold is None
        assert error == "Foobar()"
        exchange = self.db.one("SELECT * FROM exchanges")
        assert exchange
        assert exchange.amount == D('9.41')
        assert exchange.fee == D('0.59')
        assert exchange.status == 'failed'
        assert self.obama.get_credit_card_error() == 'Foobar()'
        assert self.obama.balance == P('obama').balance == 0

    def test_cch_bad_card(self):
        bob = self.make_participant('bob', is_suspicious=False)
        customer_id = bob.get_braintree_account().id
        result = braintree.PaymentMethod.create({
            "customer_id": customer_id,
            "payment_method_nonce": Nonces.Transactable
        })
        assert result.is_success
        ExchangeRoute.insert(bob, 'braintree-cc', result.payment_method.token)

        # https://developers.braintreepayments.com/ios+python/reference/general/testing#test-amounts
        # $2002 is upcharged to $2062, which corresponds to 'Invalid Tax Amount'
        self.hold, error = create_card_hold(self.db, bob, D('2002.00'))
        assert self.hold is None
        assert error.startswith('Invalid Tax Amount')

    def test_cch_multiple_cards(self):
        bob = self.make_participant('bob', is_suspicious=False)
        customer_id = bob.get_braintree_account().id

        for i in range(2):
            result = braintree.PaymentMethod.create({
                "customer_id": customer_id,
                "payment_method_nonce": Nonces.Transactable
            })
            assert result.is_success
            ExchangeRoute.insert(bob, 'braintree-cc', result.payment_method.token)

        self.hold, error = create_card_hold(self.db, bob, D('100.00'))
        assert error == ''

    def test_cch_no_card(self):
        bob = self.make_participant('bob', is_suspicious=False)
        self.hold, error = create_card_hold(self.db, bob, D('10.00'))
        assert error == 'No credit card'

    def test_cch_invalidated_card(self):
        bob = self.make_participant('bob', is_suspicious=False)
        ExchangeRoute.insert(bob, 'braintree-cc', 'foo', error='invalidated')
        self.hold, error = create_card_hold(self.db, bob, D('10.00'))
        assert error == 'No credit card'


    # capch - capture_card_hold

    def test_capch_full_amount(self):
        self.hold, error = create_card_hold(self.db, self.obama, D('20.00'))
        assert error == ''  # sanity check
        assert self.hold.status == 'authorized'

        capture_card_hold(self.db, self.obama, D('20.00'), self.hold)
        hold = braintree.Transaction.find(self.hold.id)
        assert self.obama.balance == P('obama').balance == D('20.00')
        assert self.obama.get_credit_card_error() == ''
        assert hold.status == 'submitted_for_settlement'

    def test_capch_partial_amount(self):
        self.hold, error = create_card_hold(self.db, self.obama, D('20.00'))
        assert error == ''  # sanity check

        capture_card_hold(self.db, self.obama, D('15.00'), self.hold)
        assert self.obama.balance == P('obama').balance == D('15.00')
        assert self.obama.get_credit_card_error() == ''

    def test_capch_too_high_amount(self):
        self.hold, error = create_card_hold(self.db, self.obama, D('20.00'))
        assert error == ''  # sanity check

        with self.assertRaises(Exception):
            # How do I check the exception's msg here?
            capture_card_hold(self.db, self.obama, D('20.01'), self.hold)

        assert self.obama.balance == P('obama').balance == 0

    def test_capch_amount_under_minimum(self):
        self.hold, error = create_card_hold(self.db, self.obama, D('20.00'))
        assert error == ''  # sanity check

        capture_card_hold(self.db, self.obama, D('0.01'), self.hold)
        assert self.obama.balance == P('obama').balance == D('9.41')
        assert self.obama.get_credit_card_error() == ''


    # grprbn - get_ready_payout_routes_by_network

    def test_grprbn_that_its_empty_to_start_with(self):
        assert get_ready_payout_routes_by_network(self.db, 'paypal') == []

    def test_grprbn_includes_team_owners(self):
        enterprise = self.make_team(is_approved=True)
        self.obama.set_payment_instruction(enterprise, 100)
        self.run_payday()
        routes = get_ready_payout_routes_by_network(self.db, 'paypal')
        assert [r.participant.username for r in routes] == ['picard']


    def run_payday_with_member(self):
        enterprise = self.make_team(is_approved=True, available=50)
        enterprise.add_member(self.homer, P('picard'))
        self.obama.set_payment_instruction(enterprise, 100)
        self.run_payday()
        return enterprise

    def test_grprbn_includes_team_members(self):
        self.run_payday_with_member()
        routes = get_ready_payout_routes_by_network(self.db, 'paypal')
        assert list(sorted([r.participant.username for r in routes])) == ['homer', 'picard']

    def test_grprbn_includes_former_team_members(self):
        enterprise = self.run_payday_with_member()
        enterprise.remove_member(self.homer, P('picard'))
        routes = get_ready_payout_routes_by_network(self.db, 'paypal')
        assert list(sorted([r.participant.username for r in routes])) == ['homer', 'picard']

    def test_grprbn_excludes_member_with_no_verified_identity(self):
        self.run_payday_with_member()
        self.homer.clear_identity(self.homer.list_identity_metadata()[0].country.id)
        routes = get_ready_payout_routes_by_network(self.db, 'paypal')
        assert [r.participant.username for r in routes] == ['picard']


    def test_grprbn_includes_1_0_payouts(self):
        alice = self.make_participant( 'alice'
                                     , balance=24
                                     , status_of_1_0_payout='pending-payout'
                                     , claimed_time='now'
                                      )
        ExchangeRoute.insert(alice, 'paypal', 'alice@example.com')
        routes = get_ready_payout_routes_by_network(self.db, 'paypal')
        assert [r.participant.username for r in routes] == ['alice']


class TestsWithoutBillingHarness(Harness):

    def prep(self, amount):
        """Given a dollar amount as a string, return a 3-tuple.

        The return tuple is like the one returned from _prep_hit, but with the
        second value, a log message, removed.

        """
        typecheck(amount, unicode)
        out = list(_prep_hit(D(amount)))
        out = [out[0]] + out[2:]
        return tuple(out)

    def test_prep_hit_basically_works(self):
        actual = _prep_hit(D('20.00'))
        expected = (2091,
                    u'2091 cents ($20.00 + $0.91 fee = $20.91)',
                    D('20.91'), D('0.91'))
        assert actual == expected

    def test_prep_hit_full_in_rounded_case(self):
        actual = _prep_hit(D('5.00'))
        expected = (1000,
                    u'1000 cents ($9.41 [rounded up from $5.00] + $0.59 fee = $10.00)',
                    D('10.00'), D('0.59'))
        assert actual == expected

    def test_prep_hit_at_ten_dollars(self):
        actual = self.prep(u'10.00')
        expected = (1061, D('10.61'), D('0.61'))
        assert actual == expected

    def test_prep_hit_at_forty_cents(self):
        actual = self.prep(u'0.40')
        expected = (1000, D('10.00'), D('0.59'))
        assert actual == expected

    def test_prep_hit_at_fifty_cents(self):
        actual = self.prep(u'0.50')
        expected = (1000, D('10.00'), D('0.59'))
        assert actual == expected

    def test_prep_hit_at_sixty_cents(self):
        actual = self.prep(u'0.60')
        expected = (1000, D('10.00'), D('0.59'))
        assert actual == expected

    def test_prep_hit_at_eighty_cents(self):
        actual = self.prep(u'0.80')
        expected = (1000, D('10.00'), D('0.59'))
        assert actual == expected

    def test_prep_hit_at_nine_fifteen(self):
        actual = self.prep(u'9.15')
        expected = (1000, D('10.00'), D('0.59'))
        assert actual == expected

    def test_prep_hit_at_nine_forty(self):
        actual = self.prep(u'9.40')
        expected = (1000, D('10.00'), D('0.59'))
        assert actual == expected

    def test_prep_hit_at_nine_forty_one(self):
        actual = self.prep(u'9.41')
        expected = (1000, D('10.00'), D('0.59'))
        assert actual == expected

    def test_prep_hit_at_nine_forty_two(self):
        actual = self.prep(u'9.42')
        expected = (1002, D('10.02'), D('0.60'))
        assert actual == expected


    # re - record_exchange

    def test_re_records_exchange(self):
        alice = self.make_participant('alice', last_bill_result='')
        record_exchange( self.db
                       , ExchangeRoute.from_network(alice, 'braintree-cc')
                       , amount=D("0.59")
                       , fee=D("0.41")
                       , participant=alice
                       , status='pre'
                        )
        actual = self.db.one("""
            SELECT amount, fee, participant, status, route
              FROM exchanges
        """, back_as=dict)
        expected = { "amount": D('0.59')
                   , "fee": D('0.41')
                   , "participant": "alice"
                   , "status": 'pre'
                   , "route": ExchangeRoute.from_network(alice, 'braintree-cc').id
                    }
        assert actual == expected

    def test_re_requires_valid_route(self):
        alice = self.make_participant('alice', last_bill_result='')
        bob = self.make_participant('bob', last_bill_result='')
        with self.assertRaises(AssertionError):
            record_exchange( self.db
                           , ExchangeRoute.from_network(bob, 'braintree-cc')
                           , amount=D("0.59")
                           , fee=D("0.41")
                           , participant=alice
                           , status='pre'
                            )

    def test_re_stores_error_in_note(self):
        alice = self.make_participant('alice', last_bill_result='')
        record_exchange( self.db
                       , ExchangeRoute.from_network(alice, 'braintree-cc')
                       , amount=D("0.59")
                       , fee=D("0.41")
                       , participant=alice
                       , status='pre'
                       , error='Card payment failed'
                        )
        exchange = self.db.one("SELECT * FROM exchanges")
        assert exchange.note == 'Card payment failed'

    def test_re_doesnt_update_balance_for_positive_amounts(self):
        alice = self.make_participant('alice', last_bill_result='')
        record_exchange( self.db
                       , ExchangeRoute.from_network(alice, 'braintree-cc')
                       , amount=D("0.59")
                       , fee=D("0.41")
                       , participant=alice
                       , status='pre'
                        )
        assert P('alice').balance == D('0.00')

    def test_re_updates_balance_for_negative_amounts(self):
        alice = self.make_participant('alice', balance=50, last_paypal_result='')
        record_exchange( self.db
                       , ExchangeRoute.from_network(alice, 'paypal')
                       , amount=D('-35.84')
                       , fee=D('0.75')
                       , participant=alice
                       , status='pre'
                        )
        assert P('alice').balance == D('13.41')

    def test_re_fails_if_negative_balance(self):
        alice = self.make_participant('alice', last_paypal_result='')
        ba = ExchangeRoute.from_network(alice, 'paypal')
        with pytest.raises(NegativeBalance):
            record_exchange(self.db, ba, D("-10.00"), D("0.41"), alice, 'pre')

    def test_re_result_restores_balance_on_error(self):
        alice = self.make_participant('alice', balance=30, last_paypal_result='')
        ba = ExchangeRoute.from_network(alice, 'paypal')
        e_id = record_exchange(self.db, ba, D('-27.06'), D('0.81'), alice, 'pre')
        assert alice.balance == D('02.13')
        record_exchange_result(self.db, e_id, 'failed', 'SOME ERROR', alice)
        assert P('alice').balance == D('30.00')

    def test_re_result_restores_balance_on_error_with_invalidated_route(self):
        alice = self.make_participant('alice', balance=37, last_paypal_result='')
        pp = ExchangeRoute.from_network(alice, 'paypal')
        e_id = record_exchange(self.db, pp, D('-32.45'), D('0.86'), alice, 'pre')
        assert alice.balance == D('3.69')
        pp.update_error('invalidated')
        record_exchange_result(self.db, e_id, 'failed', 'oops', alice)
        alice = P('alice')
        assert alice.balance == D('37.00')
        assert pp.error == alice.get_paypal_error() == 'invalidated'

    def test_re_result_doesnt_restore_balance_on_success(self):
        alice = self.make_participant('alice', balance=50, last_paypal_result='')
        ba = ExchangeRoute.from_network(alice, 'paypal')
        e_id = record_exchange(self.db, ba, D('-43.98'), D('1.60'), alice, 'pre')
        assert alice.balance == D('4.42')
        record_exchange_result(self.db, e_id, 'succeeded', None, alice)
        assert P('alice').balance == D('4.42')

    def test_re_result_updates_balance_for_positive_amounts(self):
        alice = self.make_participant('alice', balance=4, last_bill_result='')
        cc = ExchangeRoute.from_network(alice, 'braintree-cc')
        e_id = record_exchange(self.db, cc, D('31.59'), D('0.01'), alice, 'pre')
        assert alice.balance == D('4.00')
        record_exchange_result(self.db, e_id, 'succeeded', None, alice)
        assert P('alice').balance == D('35.59')
