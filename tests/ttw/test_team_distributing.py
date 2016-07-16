from __future__ import absolute_import, division, print_function, unicode_literals

import time
from gratipay.testing import BrowserHarness


class Tests(BrowserHarness):

    def test_owner_can_add_a_member(self):
        self.make_team(available=500)

        self.make_participant( 'alice'
                             , claimed_time='now'
                             , email_address='alice@example.com'
                             , verified_in='TT'
                              )

        self.sign_in('picard')
        self.visit('/TheEnterprise/distributing/')
        self.css('#lookup-container #query').first.fill('alice')
        time.sleep(0.1)
        self.css('#lookup-container button').first.click()
        assert [a.text for a in self.css('table#team a')] == ['alice']
