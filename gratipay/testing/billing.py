from __future__ import absolute_import, division, print_function, unicode_literals

import itertools

import balanced
import braintree
from braintree.test.nonces import Nonces

from gratipay.models.exchange_route import ExchangeRoute
from gratipay.testing import Harness
from gratipay.testing.vcr import use_cassette


class BillingHarness(Harness):

    def setUp(self):
        # Balanced Customer without funding instruments
        self.david = self.make_participant('david', is_suspicious=False,
                                           claimed_time='now',
                                           balanced_customer_href=self.david_href)

        # Balanced Customer with CC attached
        self.janet = self.make_participant('janet', is_suspicious=False,
                                           claimed_time='now',
                                           balanced_customer_href=self.janet_href)
        self.janet_route = ExchangeRoute.insert(self.janet, 'balanced-cc', self.card_href)

        # Balanced Customer with BA attached
        self.homer = self.make_participant('homer', is_suspicious=False,
                                           claimed_time='now',
                                           balanced_customer_href=self.homer_href)
        self.homer_route = ExchangeRoute.insert(self.homer, 'balanced-ba', self.bank_account_href)

        # Braintree Customer without funding instruments
        self.roman = self.make_participant('roman', is_suspicious=False,
                                         claimed_time='now',
                                         braintree_customer_id=self.roman_bt_id)
        # Braintree Customer with CC attached
        self.obama = self.make_participant('obama', is_suspicious=False,
                                          claimed_time='now',
                                          braintree_customer_id=self.obama_bt_id)
        self.obama_route = ExchangeRoute.insert(self.obama, 'braintree-cc', self.obama_cc_token)

    @classmethod
    def tearDownClass(cls):
        has_exchange_id = balanced.Transaction.f.meta.contains('exchange_id')
        credits = balanced.Credit.query.filter(has_exchange_id)
        debits = balanced.Debit.query.filter(has_exchange_id)
        for t in itertools.chain(credits, debits):
            t.meta.pop('exchange_id')
            t.save()
        super(BillingHarness, cls).tearDownClass()


with use_cassette('BillingHarness'):
    cls = BillingHarness
    balanced.configure(balanced.APIKey().save().secret)
    mp = balanced.Marketplace.my_marketplace
    if not mp:
        mp = balanced.Marketplace().save()
    cls.balanced_marketplace = mp

    cls.david_href = cls.make_balanced_customer()

    cls.janet_href = cls.make_balanced_customer()
    cls.card = balanced.Card(
        number='4111111111111111',
        expiration_month=10,
        expiration_year=2020,
        address={
            'line1': "123 Main Street",
            'state': 'Confusion',
            'postal_code': '90210',
        },
        # gratipay stores some of the address data in the meta fields,
        # continue using them to support backwards compatibility
        meta={
            'address_2': 'Box 2',
            'city_town': '',
            'region': 'Confusion',
        }
    ).save()
    cls.card.associate_to_customer(cls.janet_href)
    cls.card_href = unicode(cls.card.href)

    cls.homer_href = cls.make_balanced_customer()
    cls.bank_account = balanced.BankAccount(
        name='Homer Jay',
        account_number='112233a',
        routing_number='121042882',
    ).save()
    cls.bank_account.associate_to_customer(cls.homer_href)
    cls.bank_account_href = unicode(cls.bank_account.href)

    cls.roman_bt_id = braintree.Customer.create().customer.id

    cls.obama_bt_id = braintree.Customer.create().customer.id

    cls.bt_card = braintree.PaymentMethod.create({
        "customer_id": cls.obama_bt_id,
        "payment_method_nonce": Nonces.Transactable
    }).payment_method

    cls.obama_cc_token = cls.bt_card.token
