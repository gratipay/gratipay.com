# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import re
from gratipay.testing import BrowserHarness, QueuedEmailHarness


class Tests(BrowserHarness, QueuedEmailHarness):

    def test_can_verify_email(self):
        self.make_participant('alice', claimed_time='now')
        self.sign_in('alice')
        self.visit('/~alice/emails/')
        self.css('#content input').fill('alice@example.com')
        self.css('#content button').click()
        self.wait_for_success()

        verification_email = self.get_last_email()
        verification_link = re.match( r'.*?(http.*?$).*'
                                    , verification_email['body_text']
                                    , re.DOTALL | re.MULTILINE
                                     ).groups()[0]

        self.visit(verification_link)
        assert self.css('#content h1').text == 'Success!'
