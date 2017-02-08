# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing import BrowserHarness


class Tests(BrowserHarness):

    def test_sending_a_confirmation_email_appears_to_work(self):
        self.make_package()
        self.make_participant('bob', claimed_time='now')
        self.sign_in('bob')
        self.visit('/on/npm/foo/')
        self.css('input[type=radio]')[0].click()
        self.css('button')[0].click()
        assert self.has_element('.notification.notification-success', 1)
        assert self.has_text('Check alice@example.com for a confirmation email.')
