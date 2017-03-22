from __future__ import absolute_import, division, print_function, unicode_literals

from braintree.test.nonces import Nonces

from gratipay.testing import P
from gratipay.testing.billing import BillingHarness
from gratipay.models.exchange_route import ExchangeRoute


class TestRoutes(BillingHarness):

    def hit(self, username, action, network, address, expected=200):
        r =  self.client.POST('/~%s/routes/%s.json' % (username, action),
                              data=dict(network=network, address=address),
                              auth_as=username, raise_immediately=False)
        assert r.code == expected
        return r

    def test_associate_and_delete_valid_card(self):
        self.hit('roman', 'associate', 'braintree-cc', Nonces.Transactable)

        customer = self.roman.get_braintree_account()
        cards = customer.credit_cards
        assert len(cards) == 1
        assert self.roman.get_credit_card_error() == ''

        address = cards[0].token
        self.hit('roman', 'delete', 'braintree-cc', address)

        customer = self.roman.get_braintree_account()
        assert len(customer.credit_cards) == 0

        roman = P('roman')
        assert roman.get_credit_card_error() is None
        assert self.db.one('select is_deleted from exchange_routes '
                           'where address=%s', (address,))
        assert roman.braintree_customer_id

    def test_associate_invalid_card(self):
        self.hit('roman', 'associate', 'braintree-cc', 'an-invalid-nonce', expected=400)
        assert self.roman.get_credit_card_error() is None


    def test_associate_and_delete_valid_paypal(self):
        self.add_and_verify_email(self.roman, 'roman@gmail.com')

        self.hit('roman', 'associate', 'paypal', 'roman@gmail.com')
        assert ExchangeRoute.from_network(self.roman, 'paypal')
        assert self.roman.has_payout_route

        self.hit('roman', 'delete', 'paypal', 'roman@gmail.com')
        assert not self.roman.has_payout_route

    def test_delete_paypal_with_exchanges(self):
        self.add_and_verify_email(self.roman, 'roman@gmail.com')
        self.hit('roman', 'associate', 'paypal', 'roman@gmail.com')

        self.make_exchange('paypal', 10, 0, self.roman)
        self.hit('roman', 'delete', 'paypal', 'roman@gmail.com')

        assert not self.roman.has_payout_route

    def test_add_new_paypal_address(self):
        self.add_and_verify_email(self.roman, 'roman@gmail.com')
        self.add_and_verify_email(self.roman, 'candle@gmail.com')

        self.hit('roman', 'associate', 'paypal', 'roman@gmail.com')
        self.hit('roman', 'delete', 'paypal', 'roman@gmail.com')
        self.hit('roman', 'associate', 'paypal', 'candle@gmail.com')

        assert self.roman.has_payout_route
        assert ExchangeRoute.from_network(self.roman, 'paypal').address == 'candle@gmail.com'

    def test_revive_previous_paypal_address(self):
        self.add_and_verify_email(self.roman, 'roman@gmail.com')
        self.add_and_verify_email(self.roman, 'candle@gmail.com')

        self.hit('roman', 'associate', 'paypal', 'roman@gmail.com')
        self.hit('roman', 'delete', 'paypal', 'roman@gmail.com')
        self.hit('roman', 'associate', 'paypal', 'candle@gmail.com')
        self.hit('roman', 'delete', 'paypal', 'candle@gmail.com')
        self.hit('roman', 'associate', 'paypal', 'roman@gmail.com')

        assert self.roman.has_payout_route
        assert ExchangeRoute.from_network(self.roman, 'paypal').address == 'roman@gmail.com'

    def test_associate_paypal_invalid(self):
        r = self.hit('roman', 'associate', 'paypal', 'alice@gmail.com', expected=400)
        assert not ExchangeRoute.from_network(self.roman, 'paypal')
        assert not self.roman.has_payout_route
        assert "Only verified email addresses allowed." in r.body


    def test_credit_card_page(self):
        self.make_participant('alice', claimed_time='now')
        actual = self.client.GET('/~alice/routes/credit-card', auth_as='alice').body
        assert "ZIP or Postal Code" in actual

    def test_credit_card_page_loads_when_there_is_a_braintree_card(self):
        expected = 'Current: '
        actual = self.client.GET('/~obama/routes/credit-card', auth_as='obama').body.decode('utf8')
        assert expected in actual

    def test_credit_card_page_shows_details_for_braintree_cards(self):
        response = self.client.GET('/~obama/routes/credit-card', auth_as='obama').body.decode('utf8')
        assert self.bt_card.masked_number in response

    def test_receipt_page_loads_for_braintree_cards(self):
        ex_id = self.make_exchange(self.obama_route, 113, 30, self.obama)
        url_receipt = '/~obama/receipts/{}.html'.format(ex_id)
        actual = self.client.GET(url_receipt, auth_as='obama').body.decode('utf8')
        assert self.bt_card.card_type in actual
