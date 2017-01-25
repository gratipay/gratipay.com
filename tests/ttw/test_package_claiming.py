# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing import BrowserHarness


class Tests(BrowserHarness):

    def test_sending_a_confirmation_email_works(self):
        self.make_package()
        self.make_participant('alice', claimed_time='now')
        self.sign_in('alice')
        self.visit('/on/npm/foo/')
        self.css('input[type=radio]').click()
        self.css('button').click()
        assert self.has_element('.notification.notification-success', 1)
        assert self.has_text('A confirmation email has been sent')
