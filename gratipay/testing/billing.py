"""
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import braintree
import mock
from braintree.test.nonces import Nonces

from gratipay.billing.payday import Payday
from gratipay.billing.exchanges import cancel_card_hold
from gratipay.models.exchange_route import ExchangeRoute

from .harness import Harness
from .vcr import use_cassette


class PaydayMixin(object):

    @mock.patch.object(Payday, 'fetch_card_holds')
    def run_payday(self, fch):
        fch.return_value = {}
        return self.app.payday_runner.run_payday()

    def start_payday(self):
        return self.app.payday_runner._start_payday()


class BillingHarness(Harness, PaydayMixin):
    """This is a harness for billing-related tests.
    """

    _fixture_installed = False

    def setUp(self):
        if not BillingHarness._fixture_installed:
            install_fixture()

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
        self.homer = self.make_participant('homer', is_suspicious=False, verified_in='US',
                                           claimed_time='now', email_address='abcd@gmail.com')
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


def install_fixture():
    with use_cassette('BillingHarness'):
        cls = BillingHarness
        cls.roman_bt_id = braintree.Customer.create().customer.id
        cls.obama_bt_id = braintree.Customer.create().customer.id
        cls.bt_card = braintree.PaymentMethod.create({
            "customer_id": cls.obama_bt_id,
            "payment_method_nonce": Nonces.Transactable
        }).payment_method
        cls.obama_cc_token = cls.bt_card.token
        cls._fixture_installed = True
