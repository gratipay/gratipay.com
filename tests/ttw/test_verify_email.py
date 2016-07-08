from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing import BrowserHarness


class Tests(BrowserHarness):

    def test_clicking_resend_doesnt_error(self):
        self.make_participant('alice', claimed_time='now')
        self.sign_in('alice')
        self.visit('/~alice/emails/verify.html?email=alice@gratipay.com&nonce=abcd')
        assert self.has_text('The verification code for alice@gratipay.com is bad.')
        self.css('button.resend').click()
        assert self.has_element('.notification.notification-success', 2)
        assert self.has_text('A verification email has been sent')
