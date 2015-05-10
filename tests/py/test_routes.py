from __future__ import absolute_import, division, print_function, unicode_literals

import balanced
from braintree.test.nonces import Nonces
import mock

from gratipay.testing.billing import BillingHarness
from gratipay.models.exchange_route import ExchangeRoute
from gratipay.models.participant import Participant


class TestRoutes(BillingHarness):

    def hit(self, username, action, network, address, expected=200):
        r =  self.client.POST('/%s/routes/%s.json' % (username, action),
                              data=dict(network=network, address=address),
                              auth_as=username, raise_immediately=False)
        assert r.code == expected
        return r

    # Remove this once we've dumped 'balanced-cc' altogether
    def test_associate_balanced_card_should_fail(self):
        card = balanced.Card(
            number='4242424242424242',
            expiration_year=2020,
            expiration_month=12
        ).save()
        customer = self.david.get_balanced_account()
        self.hit('david', 'associate', 'balanced-cc', card.href, expected=400)

        cards = customer.cards.all()
        assert len(cards) == 0

    def test_associate_and_delete_valid_card(self):
        self.hit('roman', 'associate', 'braintree-cc', Nonces.Transactable)

        customer = self.roman.get_braintree_account()
        cards = customer.credit_cards
        assert len(cards) == 1
        assert self.roman.get_credit_card_error() == ''

        self.hit('roman', 'delete', 'braintree-cc', cards[0].token)

        customer = self.roman.get_braintree_account()
        assert len(customer.credit_cards) == 0

        roman = Participant.from_username('roman')
        assert roman.get_credit_card_error() == 'invalidated'
        assert roman.braintree_customer_id

    def test_associate_invalid_card(self):
        self.hit('roman', 'associate', 'braintree-cc', 'an-invalid-nonce', expected=400)
        assert self.roman.get_credit_card_error() is None

    def test_associate_and_delete_bank_account_valid(self):
        bank_account = balanced.BankAccount( name='Alice G. Krebs'
                                           , routing_number='321174851'
                                           , account_number='9900000001'
                                           , account_type='checking'
                                            ).save()
        customer = self.david.get_balanced_account()
        customer.merchant_status = 'underwritten'
        with mock.patch.object(Participant, 'get_balanced_account') as gba:
            gba.return_value = customer
            self.hit('david', 'associate', 'balanced-ba', bank_account.href)

        bank_accounts = customer.bank_accounts.all()
        assert len(bank_accounts) == 1
        assert bank_accounts[0].href == bank_account.href

        assert self.david.get_bank_account_error() == ''

        self.hit('david', 'delete', 'balanced-ba', bank_account.href)

        david = Participant.from_username('david')
        route = ExchangeRoute.from_address(david, 'balanced-ba', bank_account.href)
        assert route.error == david.get_bank_account_error() == 'invalidated'
        assert david.balanced_customer_href

        # Check that update_error doesn't update an invalidated route
        route.update_error('some error')
        assert route.error == david.get_bank_account_error() == 'invalidated'

    @mock.patch.object(Participant, 'get_balanced_account')
    def test_associate_bank_account_invalid(self, gba):
        gba.return_value.merchant_status = 'underwritten'
        self.hit('david', 'associate', 'balanced-ba', '/bank_accounts/BA123123123', expected=400)
        assert self.david.get_bank_account_error() is None

    def test_associate_bitcoin(self):
        addr = '17NdbrSGoUotzeGCcMMCqnFkEvLymoou9j'
        self.hit('david', 'associate', 'bitcoin', addr)
        route = ExchangeRoute.from_network(self.david, 'bitcoin')
        assert route.address == addr
        assert route.error == ''

    def test_associate_bitcoin_invalid(self):
        self.hit('david', 'associate', 'bitcoin', '12345', expected=400)
        assert not ExchangeRoute.from_network(self.david, 'bitcoin')

    def test_bank_account(self):
        expected = "add or change your bank account"
        actual = self.client.GET('/alice/routes/bank-account.html').body
        assert expected in actual

    def test_bank_account_auth(self):
        self.make_participant('alice', claimed_time='now')
        expected = '<em id="status">not connected</em>'
        actual = self.client.GET('/alice/routes/bank-account.html', auth_as='alice').body
        assert expected in actual

    def test_credit_card(self):
        self.make_participant('alice', claimed_time='now')
        expected = "add or change your credit card"
        actual = self.client.GET('/alice/routes/credit-card.html').body
        assert expected in actual

    def test_credit_card_page_shows_card_missing(self):
        self.make_participant('alice', claimed_time='now')
        expected = 'Your credit card is <em id="status">missing'
        actual = self.client.GET('/alice/routes/credit-card.html', auth_as='alice').body.decode('utf8')
        assert expected in actual

    def test_credit_card_page_loads_when_there_is_a_balanced_card(self):
        expected = 'Your credit card is <em id="status">working'
        actual = self.client.GET('/janet/routes/credit-card.html', auth_as='janet').body.decode('utf8')
        assert expected in actual

    def test_credit_card_page_shows_details_for_balanced_cards(self):
        response = self.client.GET('/janet/routes/credit-card.html', auth_as='janet').body.decode('utf8')
        assert self.card.number in response

    def test_credit_card_page_shows_when_balanced_card_is_failing(self):
        ExchangeRoute.from_network(self.janet, 'balanced-cc').update_error('Some error')
        expected = 'Your credit card is <em id="status">failing'
        actual = self.client.GET('/janet/routes/credit-card.html', auth_as='janet').body.decode('utf8')
        assert expected in actual

    def test_receipt_page_loads_for_balanced_cards(self):
        ex_id = self.make_exchange('balanced-cc', 113, 30, self.janet)
        url_receipt = '/janet/receipts/{}.html'.format(ex_id)
        actual = self.client.GET(url_receipt, auth_as='janet').body.decode('utf8')
        assert 'Visa' in actual
