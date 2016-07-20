from __future__ import absolute_import, division, print_function, unicode_literals

import time
from gratipay.testing import BrowserHarness, D,P


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
        self.css('.lookup-container .query').first.fill('alice')
        time.sleep(0.1)
        self.css('.lookup-container button').first.click()
        assert [a.text for a in self.css('table.team a')] == ['alice']


    def test_owner_can_remove_a_member(self):
        enterprise = self.make_team(available=500)
        alice = self.make_participant( 'alice'
                                     , claimed_time='now'
                                     , email_address='alice@example.com'
                                     , verified_in='TT'
                                      )
        enterprise.add_member(alice, P('picard'))

        self.sign_in('picard')
        self.visit('/TheEnterprise/distributing/')
        self.css('table.team span.remove').first.click()
        time.sleep(0.1)
        self.get_alert().accept()
        time.sleep(0.2)
        assert enterprise.get_memberships() == []


    def test_totals_are_as_expected(self):
        enterprise = self.make_team(available=500)
        alice = self.make_participant( 'alice'
                                     , claimed_time='now'
                                     , email_address='alice@example.com'
                                     , verified_in='TT'
                                      )
        bob = self.make_participant( 'bob'
                                   , claimed_time='now'
                                   , email_address='bob@example.com'
                                   , verified_in='TT'
                                    )
        enterprise.add_member(alice, P('picard'))
        enterprise.add_member(bob, P('picard'))

        enterprise.set_take_for(alice, D('5.00'), alice)
        enterprise.set_take_for(bob, D('37.00'), bob)

        self.visit('/TheEnterprise/distributing/')

        assert self.css('tr.totals .take').first.text == '42.00'
        assert self.css('tr.totals .balance').first.text == '458.00'
        assert self.css('tr.totals .percentage').first.text == '91.6'
