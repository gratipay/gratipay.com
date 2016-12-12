# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing import BrowserHarness


class Tests(BrowserHarness):

    def check(self, status, has_request_button, has_check_button):
        self.make_participant('alice', claimed_time='now', status_of_1_0_payout=status)
        self.sign_in('alice')
        self.visit('/~alice/settings/')

        self.css('.account-details a button')
        assert self.has_text('Request 1.0 Payout') is has_request_button

        self.css('.account-details a button')
        assert self.has_text('Check 1.0 Payout') is has_check_button

    def test_too_little_has_neither(self):
        self.check('too-little', False, False)

    def test_pending_application_has_request_button(self):
        self.check('pending-application', True, False)

    def test_pending_review_has_check_button(self):
        self.check('pending-review', False, True)

    def test_rejected_has_neither(self):
        self.check('rejected', False, False)

    def test_pending_payout_has_check_button(self):
        self.check('pending-payout', False, True)

    def test_pending_completed_has_neither(self):
        self.check('completed', False, False)
