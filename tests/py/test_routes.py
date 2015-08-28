from __future__ import absolute_import, division, print_function, unicode_literals

from braintree.test.nonces import Nonces
import mock

from gratipay.testing.billing import BillingHarness
from gratipay.models.exchange_route import ExchangeRoute
from gratipay.models.participant import Participant


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

        self.hit('roman', 'delete', 'braintree-cc', cards[0].token)

        customer = self.roman.get_braintree_account()
        assert len(customer.credit_cards) == 0

        roman = Participant.from_username('roman')
        assert roman.get_credit_card_error() == 'invalidated'
        assert roman.braintree_customer_id

    def test_associate_invalid_card(self):
        self.hit('roman', 'associate', 'braintree-cc', 'an-invalid-nonce', expected=400)
        assert self.roman.get_credit_card_error() is None

    @mock.patch.object(Participant, 'send_email')
    def test_associate_paypal(self, mailer):
        mailer.return_value = 1 # Email successfully sent
        self.roman.add_email('roman@gmail.com')
        self.db.run("UPDATE emails SET verified=true WHERE address='roman@gmail.com'")
        self.hit('roman', 'associate', 'paypal', 'roman@gmail.com')
        assert ExchangeRoute.from_network(self.roman, 'paypal')
        assert self.roman.has_payout_route

    def test_associate_paypal_invalid(self):
        r = self.hit('roman', 'associate', 'paypal', 'alice@gmail.com', expected=400)
        assert not ExchangeRoute.from_network(self.roman, 'paypal')
        assert not self.roman.has_payout_route
        assert "Only verified email addresses allowed." in r.body

    def test_associate_bitcoin(self):
        addr = '17NdbrSGoUotzeGCcMMCqnFkEvLymoou9j'
        self.hit('roman', 'associate', 'bitcoin', addr)
        route = ExchangeRoute.from_network(self.roman, 'bitcoin')
        assert route.address == addr
        assert route.error == ''

    def test_associate_bitcoin_invalid(self):
        self.hit('roman', 'associate', 'bitcoin', '12345', expected=400)
        assert not ExchangeRoute.from_network(self.roman, 'bitcoin')

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
