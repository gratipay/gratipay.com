# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing import Harness


class TestSupportGratipay(Harness):

    def shown(self, to=None):
        return 'of active users also' in self.client.GET('/', auth_as=to).body

    def test_not_shown_to_anon(self):
        assert not self.shown()

    def test_not_shown_to_dormant_auth(self):
        self.make_participant('alice', claimed_time='now')
        assert not self.shown('alice')

    def test_shown_when_on_the_fence(self):
        alice = self.make_participant('alice', claimed_time='now', last_bill_result='')
        Enterprise = self.make_team(is_approved=True)
        alice.set_payment_instruction(Enterprise, '1.00')
        assert self.shown('alice')
        return alice

    def test_not_shown_to_free_rider(self):
        alice = self.test_shown_when_on_the_fence()
        alice.update_is_free_rider(True)
        assert not self.shown('alice')

    def test_not_shown_to_giver_to_Gratipay(self):
        alice = self.test_shown_when_on_the_fence()
        Gratipay = self.make_team('Gratipay', is_approved=True)
        alice.set_payment_instruction(Gratipay, '0.10')
        assert not self.shown('alice')


    def check_button(self, lang, decimal, currency):
        self.test_shown_when_on_the_fence()
        body = self.client.GET( '/'
                              , auth_as='alice'
                              , HTTP_ACCEPT_LANGUAGE=str(lang)
                               ).body.decode('utf8')
        target = '<button class="low" data-amount="{}">{}</button>'.format(decimal, currency)
        assert target in body

    def test_amount_on_button_is_as_expected_in_english(self):
        self.check_button('en', '0.05', '$0.05')

    def test_amount_on_button_is_as_expected_in_italian(self):
        self.check_button('it', '0,05', 'US$\xa00,05')
