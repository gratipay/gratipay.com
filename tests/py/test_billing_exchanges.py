from __future__ import absolute_import, division, print_function, unicode_literals

from decimal import Decimal as D

import braintree
from braintree.test.nonces import Nonces
import mock
import pytest

from aspen.utils import typecheck
from gratipay.billing.exchanges import (
    _prep_hit,
    ach_credit,
    cancel_card_hold,
    capture_card_hold,
    create_card_hold,
    record_exchange,
    record_exchange_result,
    skim_credit,
    sync_with_balanced,
)
from gratipay.exceptions import NegativeBalance, NotWhitelisted
from gratipay.models.exchange_route import ExchangeRoute
from gratipay.models.participant import Participant
from gratipay.testing import Foobar, Harness
from gratipay.testing.billing import BillingHarness


class TestCardHolds(BillingHarness):

    # create_card_hold

    def test_create_card_hold_success(self):
        hold, error = create_card_hold(self.db, self.obama, D('1.00'))
        obama = Participant.from_id(self.obama.id)
        assert isinstance(hold, braintree.Transaction)
        assert hold.status == 'authorized'
        assert hold.amount == D('10.00')
        assert error == ''
        assert self.obama.balance == obama.balance == 0

    def test_create_card_hold_for_suspicious_raises_NotWhitelisted(self):
        bob = self.make_participant('bob', is_suspicious=True,
                                    balanced_customer_href='fake_href')
        with self.assertRaises(NotWhitelisted):
            create_card_hold(self.db, bob, D('1.00'))

    @mock.patch('braintree.Transaction.sale')
    def test_create_card_hold_failure(self, btsale):
        btsale.side_effect = Foobar
        hold, error = create_card_hold(self.db, self.obama, D('1.00'))
        assert hold is None
        assert error == "Foobar()"
        exchange = self.db.one("SELECT * FROM exchanges")
        assert exchange
        assert exchange.amount == D('9.41')
        assert exchange.fee == D('0.59')
        assert exchange.status == 'failed'
        obama = Participant.from_id(self.obama.id)
        assert self.obama.get_credit_card_error() == 'Foobar()'
        assert self.obama.balance == obama.balance == 0

    def test_create_card_hold_bad_card(self):
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
        hold, error = create_card_hold(self.db, bob, D('2002.00'))
        assert hold is None
        assert error.startswith('Invalid Tax Amount')

    def test_create_card_hold_multiple_cards(self):
        bob = self.make_participant('bob', is_suspicious=False)
        customer_id = bob.get_braintree_account().id

        for i in range(2):
            result = braintree.PaymentMethod.create({
                "customer_id": customer_id,
                "payment_method_nonce": Nonces.Transactable
            })
            assert result.is_success
            ExchangeRoute.insert(bob, 'braintree-cc', result.payment_method.token)

        hold, error = create_card_hold(self.db, bob, D('100.00'))
        assert error == ''

        # Clean up
        cancel_card_hold(hold)

    def test_create_card_hold_no_card(self):
        bob = self.make_participant('bob', is_suspicious=False)
        hold, error = create_card_hold(self.db, bob, D('10.00'))
        assert error == 'No credit card'

    def test_create_card_hold_invalidated_card(self):
        bob = self.make_participant('bob', is_suspicious=False)
        ExchangeRoute.insert(bob, 'braintree-cc', 'foo', error='invalidated')
        hold, error = create_card_hold(self.db, bob, D('10.00'))
        assert error == 'No credit card'

    # capture_card_hold

    def test_capture_card_hold_full_amount(self):
        hold, error = create_card_hold(self.db, self.obama, D('20.00'))
        assert error == ''  # sanity check
        assert hold.status == 'authorized'

        capture_card_hold(self.db, self.obama, D('20.00'), hold)
        hold = braintree.Transaction.find(hold.id)
        obama = Participant.from_id(self.obama.id)
        assert self.obama.balance == obama.balance == D('20.00')
        assert self.obama.get_credit_card_error() == ''
        assert hold.status == 'submitted_for_settlement'

        # Clean up
        cancel_card_hold(hold)

    def test_capture_card_hold_partial_amount(self):
        hold, error = create_card_hold(self.db, self.obama, D('20.00'))
        assert error == ''  # sanity check

        capture_card_hold(self.db, self.obama, D('15.00'), hold)
        obama = Participant.from_id(self.obama.id)
        assert self.obama.balance == obama.balance == D('15.00')
        assert self.obama.get_credit_card_error() == ''

        # Clean up
        cancel_card_hold(hold)

    def test_capture_card_hold_too_high_amount(self):
        hold, error = create_card_hold(self.db, self.obama, D('20.00'))
        assert error == ''  # sanity check

        with self.assertRaises(Exception):
            # How do I check the exception's msg here?
            capture_card_hold(self.db, self.obama, D('20.01'), hold)

        obama = Participant.from_id(self.obama.id)
        assert self.obama.balance == obama.balance == 0

        # Clean up
        cancel_card_hold(hold)

    def test_capture_card_hold_amount_under_minimum(self):
        hold, error = create_card_hold(self.db, self.obama, D('20.00'))
        assert error == ''  # sanity check

        capture_card_hold(self.db, self.obama, D('0.01'), hold)
        obama = Participant.from_id(self.obama.id)
        assert self.obama.balance == obama.balance == D('9.41')
        assert self.obama.get_credit_card_error() == ''


class TestFees(Harness):

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

    def test_skim_credit(self):
        actual = skim_credit(D('10.00'))
        assert actual == (D('10.00'), D('0.00'))


class TestRecordExchange(Harness):

    def test_record_exchange_doesnt_update_balance_for_positive_amounts(self):
        alice = self.make_participant('alice', last_bill_result='')
        record_exchange( self.db
                       , ExchangeRoute.from_network(alice, 'balanced-cc')
                       , amount=D("0.59")
                       , fee=D("0.41")
                       , participant=alice
                       , status='pre'
                        )
        alice = Participant.from_username('alice')
        assert alice.balance == D('0.00')

    def test_record_exchange_updates_balance_for_negative_amounts(self):
        alice = self.make_participant('alice', balance=50, last_ach_result='')
        record_exchange( self.db
                       , ExchangeRoute.from_network(alice, 'balanced-ba')
                       , amount=D('-35.84')
                       , fee=D('0.75')
                       , participant=alice
                       , status='pre'
                        )
        alice = Participant.from_username('alice')
        assert alice.balance == D('13.41')

    def test_record_exchange_fails_if_negative_balance(self):
        alice = self.make_participant('alice', last_ach_result='')
        ba = ExchangeRoute.from_network(alice, 'balanced-ba')
        with pytest.raises(NegativeBalance):
            record_exchange(self.db, ba, D("-10.00"), D("0.41"), alice, 'pre')

    def test_record_exchange_result_restores_balance_on_error(self):
        alice = self.make_participant('alice', balance=30, last_ach_result='')
        ba = ExchangeRoute.from_network(alice, 'balanced-ba')
        e_id = record_exchange(self.db, ba, D('-27.06'), D('0.81'), alice, 'pre')
        assert alice.balance == D('02.13')
        record_exchange_result(self.db, e_id, 'failed', 'SOME ERROR', alice)
        alice = Participant.from_username('alice')
        assert alice.balance == D('30.00')

    def test_record_exchange_result_restores_balance_on_error_with_invalidated_route(self):
        alice = self.make_participant('alice', balance=37, last_ach_result='')
        ba = ExchangeRoute.from_network(alice, 'balanced-ba')
        e_id = record_exchange(self.db, ba, D('-32.45'), D('0.86'), alice, 'pre')
        assert alice.balance == D('3.69')
        ba.update_error('invalidated')
        record_exchange_result(self.db, e_id, 'failed', 'oops', alice)
        alice = Participant.from_username('alice')
        assert alice.balance == D('37.00')
        assert ba.error == alice.get_bank_account_error() == 'invalidated'

    def test_record_exchange_result_doesnt_restore_balance_on_success(self):
        alice = self.make_participant('alice', balance=50, last_ach_result='')
        ba = ExchangeRoute.from_network(alice, 'balanced-ba')
        e_id = record_exchange(self.db, ba, D('-43.98'), D('1.60'), alice, 'pre')
        assert alice.balance == D('4.42')
        record_exchange_result(self.db, e_id, 'succeeded', None, alice)
        alice = Participant.from_username('alice')
        assert alice.balance == D('4.42')

    def test_record_exchange_result_updates_balance_for_positive_amounts(self):
        alice = self.make_participant('alice', balance=4, last_bill_result='')
        cc = ExchangeRoute.from_network(alice, 'balanced-cc')
        e_id = record_exchange(self.db, cc, D('31.59'), D('0.01'), alice, 'pre')
        assert alice.balance == D('4.00')
        record_exchange_result(self.db, e_id, 'succeeded', None, alice)
        alice = Participant.from_username('alice')
        assert alice.balance == D('35.59')
