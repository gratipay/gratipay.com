from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing import BrowserHarness


class Tests(BrowserHarness):

    def test_homepage_renders_copy_correctly_for_anon(self):
        self.browser.visit('/')
        assert self.browser.find_by_css('#content h1').html == 'Teams'

    def test_homepage_renders_copy_correctly_for_authed(self):
        self.make_participant('alice', claimed_time='now')
        self.browser.sign_in('alice')
        self.browser.visit('/')
        assert self.browser.find_by_css('#content h1').html == 'Teams'
        assert self.browser.find_by_css('.you-are a').html.strip()[:6] == '~alice'
