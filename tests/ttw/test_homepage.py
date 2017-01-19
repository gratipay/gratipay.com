from __future__ import absolute_import, division, print_function, unicode_literals

import time
from gratipay.testing import BrowserHarness


class Tests(BrowserHarness):

    def test_homepage_renders_copy_correctly_for_anon(self):
        assert self.css('#content h1').html == 'Projects'
        assert self.css('#header .sign-in button').html.strip()[:7] == 'Sign in'

    def test_homepage_renders_copy_correctly_for_authed(self):
        self.make_participant('alice', claimed_time='now')
        self.sign_in('alice')
        self.reload()
        assert self.css('#content h1').html == 'Projects'
        assert self.css('.you-are a').html.strip()[:6] == '~alice'

    def test_homepage_pops_the_welcome_modal_for_first_time_visitors(self):
        assert self.has_text('Welcome to Gratipay!')

    def test_homepage_suppresses_the_welcome_modal_once_its_clicked(self):
        self.css('.welcome button').first.click()
        time.sleep(0.1)
        self.reload()
        assert not self.has_text('Welcome to Gratipay!')
