from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing import BrowserHarness


class Tests(BrowserHarness):

    def test_sign_in_modal_is_hidden_by_default(self):
        self.visit('/')

        assert not self.css('#sign-in-modal').visible

    def test_clicking_sign_in_button_opens_up_modal(self):
        self.visit('/')

        self.css('.sign-in').click()
        assert self.css('#sign-in-modal').visible

    def test_clicking_close_closes_modal(self):
        self.visit('/')

        self.css('.sign-in').click()
        self.css('#sign-in-modal .close-modal').click()

        assert not self.css('#sign-in-modal').visible

    def test_401_page_opens_modal_automatically(self):
        self.visit('/about/me/emails.json')

        assert self.css('#sign-in-modal').visible
        assert self.css('#sign-in-modal p')[0].text == 'Enter your email to sign-in to Gratipay'
