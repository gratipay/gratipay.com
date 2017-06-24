from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing import BrowserHarness, D,P
from selenium.webdriver.common.keys import Keys


class Tests(BrowserHarness):

    def setUp(self):
        BrowserHarness.setUp(self)
        self.enterprise = self.make_team(available=500)
        self.alice = self.make_participant( 'alice'
                                          , claimed_time='now'
                                          , email_address='alice@example.com'
                                          , verified_in='TT'
                                           )


    def test_owner_can_add_a_member(self):
        self.sign_in('picard')
        self.visit('/TheEnterprise/distributing/')
        self.css('.lookup-container .query').first.fill('alice')
        self.css('.lookup-container button').first.click()
        self.wait_for('table.team a')
        assert [a.text for a in self.css('table.team a')] == ['alice']


    def set_take(self, amount):
        el = self.css('table.team form.edit input').first
        el.fill(amount)
        el.type(Keys.ENTER)


    def test_member_can_set_their_take(self):
        self.enterprise.add_member(self.alice, P('picard'))
        self.sign_in('alice')
        self.visit('/TheEnterprise/distributing/')
        self.set_take('5.37')
        assert self.wait_for_success() == 'Your take is now $5.37.'
        assert self.enterprise.get_take_for(self.alice) == D('5.37')


    def test_member_can_set_their_take_again(self):
        self.test_member_can_set_their_take()
        self.set_take('100')
        assert self.wait_for_success() == 'Your take is now $100.00.'
        assert self.enterprise.get_take_for(self.alice) == D('100.00')


    def test_owner_can_remove_a_member(self):
        self.enterprise.add_member(self.alice, P('picard'))
        self.sign_in('picard')
        self.visit('/TheEnterprise/distributing/')
        self.css('table.team span.remove').first.click()
        self.wait_for('.confirmation-modal .yes').first.click()
        assert self.wait_for_success() == 'alice has been removed from the team.'
        assert self.enterprise.get_memberships() == []


    def test_members_are_sorted_by_amount_ascending(self):
        bob = self.make_participant( 'bob'
                                   , claimed_time='now'
                                   , email_address='bob@example.com'
                                   , verified_in='TT'
                                    )
        self.enterprise.add_member(self.alice, P('picard'))
        self.enterprise.add_member(bob, P('picard'))

        self.enterprise.set_take_for(self.alice, D('5.00'), self.alice)
        self.enterprise.set_take_for(bob, D('37.00'), bob)

        self.visit('/TheEnterprise/distributing/')
        assert [a.text for a in self.css('table.team a')] == ['alice', 'bob']

        self.enterprise.set_take_for(bob, D('4.00'), bob)

        self.visit('/TheEnterprise/distributing/')
        assert [a.text for a in self.css('table.team a')] == ['bob', 'alice']


    def test_totals_are_as_expected(self):
        bob = self.make_participant( 'bob'
                                   , claimed_time='now'
                                   , email_address='bob@example.com'
                                   , verified_in='TT'
                                    )
        self.enterprise.add_member(self.alice, P('picard'))
        self.enterprise.add_member(bob, P('picard'))

        self.enterprise.set_take_for(self.alice, D('5.00'), self.alice)
        self.enterprise.set_take_for(bob, D('37.00'), bob)

        self.visit('/TheEnterprise/distributing/')

        assert self.css('tr.totals .take').first.text == '42.00'
        assert self.css('tr.totals .balance').first.text == '458.00'
        assert self.css('tr.totals .percentage').first.text == '91.6'
