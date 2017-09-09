from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing import BrowserHarness


class Tests(BrowserHarness):

    def fetch(self):
        return self.db.one('SELECT pfos.*::payments_for_open_source '
                           'FROM payments_for_open_source pfos')

    def fill_form(self, amount, credit_card_number, expiration, cvv, name, email_address,
                  follow_up, promotion_name, promotion_url, promotion_twitter, promotion_message):
        self.wait_for('.braintree-form-number')
        self.fill('amount', amount)
        with self.get_iframe('braintree-hosted-field-number') as iframe:
            iframe.fill('credit-card-number', credit_card_number)
        with self.get_iframe('braintree-hosted-field-expirationDate') as iframe:
            iframe.fill('expiration', expiration)
        with self.get_iframe('braintree-hosted-field-cvv') as iframe:
            iframe.fill('cvv', cvv)
        self.fill('name', name)
        self.fill('email_address', email_address)
        if promotion_name:
            self.css('.promotion-gate button').type('\n')
                                                # stackoverflow.com/q/11908249#comment58577676_19763087
            self.wait_for('#promotion-message')
            self.fill('promotion_name', promotion_name)
            self.fill('promotion_url', promotion_url)
            self.fill('promotion_twitter', promotion_twitter)
            self.fill('promotion_message', promotion_message)


    def test_loads_for_anon(self):
        assert self.css('#banner h1').html == 'Pay for open source.'
        assert self.css('#header .sign-in button').html.strip()[:17] == 'Sign in / Sign up'

    def test_redirects_for_authed_exclamation_point(self):
        self.make_participant('alice', claimed_time='now')
        self.sign_in('alice')
        self.reload()
        assert self.css('#banner h1').html == 'Browse'
        assert self.css('.you-are a').html.strip()[:6] == '~alice'

    def test_anon_can_post(self):
        self.fill_form('537', '4242424242424242', '1020', '123', 'Alice Liddell',
                       'alice@example.com', 'monthly', 'Wonderland', 'http://www.example.com/',
                       'thebestbutter', 'Love me! Love me! Say that you love me!')
        self.css('fieldset.submit button').type('\n')
        self.wait_for('.payment-complete', 10)
        assert self.css('.payment-complete .description').text == 'Payment complete.'
        assert self.fetch().succeeded
