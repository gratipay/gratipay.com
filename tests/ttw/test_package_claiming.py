# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing import BrowserHarness


class TestSendConfirmationLink(BrowserHarness):

    def check(self, choice=0):
        self.make_participant('bob', claimed_time='now')
        self.sign_in('bob')
        self.visit('/on/npm/foo/')
        self.css('input[type=radio]')[choice].click()
        self.css('button')[0].click()
        assert self.has_element('.notification.notification-success', 1)
        assert self.has_text('Check alice@example.com for a confirmation link.')

    def test_appears_to_work(self):
        self.make_package()
        self.check()

    def test_works_when_there_are_multiple_addresses(self):
        self.make_package(emails=['alice@example.com', 'bob@example.com'])
        self.check()

    def test_can_send_to_second_email(self):
        self.make_package(emails=['bob@example.com', 'alice@example.com'])
        self.check(choice=1)
