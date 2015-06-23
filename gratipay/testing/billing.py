from __future__ import absolute_import, division, print_function, unicode_literals

import itertools

import balanced
import braintree
from braintree.test.nonces import Nonces

from gratipay.billing.exchanges import cancel_card_hold
from gratipay.models.exchange_route import ExchangeRoute
from gratipay.testing import Harness
from gratipay.testing.vcr import use_cassette


class BillingHarness(Harness):

    def setUp(self):
        # Braintree Customer without funding instruments
        self.roman = self.make_participant('roman', is_suspicious=False,
                                         claimed_time='now',
                                         braintree_customer_id=self.roman_bt_id)
        # Braintree Customer with CC attached
        self.obama = self.make_participant('obama', is_suspicious=False,
                                          claimed_time='now',
                                          braintree_customer_id=self.obama_bt_id)
        self.obama_route = ExchangeRoute.insert(self.obama, 'braintree-cc', self.obama_cc_token)
        # A customer with Paypal attached.
        self.homer = self.make_participant('homer', is_suspicious=False,
                                           claimed_time='now')
        self.homer_route = ExchangeRoute.insert(self.homer, 'paypal', 'abcd@gmail.com')


    @classmethod
    def tearDownClass(cls):
        # Braintree Cleanup
        existing_holds = braintree.Transaction.search(
            braintree.TransactionSearch.status == 'authorized'
        )
        for hold in existing_holds.items:
            cancel_card_hold(hold)
        super(BillingHarness, cls).tearDownClass()


with use_cassette('BillingHarness'):
    cls = BillingHarness

    cls.roman_bt_id = braintree.Customer.create().customer.id

    cls.obama_bt_id = braintree.Customer.create().customer.id

    cls.bt_card = braintree.PaymentMethod.create({
        "customer_id": cls.obama_bt_id,
        "payment_method_nonce": Nonces.Transactable
    }).payment_method

    cls.obama_cc_token = cls.bt_card.token
