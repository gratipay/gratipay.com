# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import pickle
from gratipay.testing import BrowserHarness, P


class Test(BrowserHarness):

    def check(self, choice=0):
        self.make_participant('alice', claimed_time='now')
        self.sign_in('alice')
        self.visit('/on/npm/foo/')
        self.css('label')[0].click() # activate select
        self.css('label')[choice].click()
        self.css('button')[0].click()
        assert self.has_element('.notification.notification-success', 1)
        assert self.has_text('Check your inbox for a verification link.')
        return self.db.one('select address from claims c join emails e on c.nonce = e.nonce')

    def test_appears_to_work(self):
        self.make_package()
        assert self.check() == 'alice@example.com'

    def test_works_when_there_are_multiple_addresses(self):
        self.make_package(emails=['alice@example.com', 'bob@example.com'])
        assert self.check() == 'alice@example.com'

    def test_can_send_to_second_email(self):
        self.make_package(emails=['alice@example.com', 'bob@example.com'])
        assert self.check(choice=1) == 'bob@example.com'

    def test_disabled_items_are_disabled(self):
        self.make_package(emails=['alice@example.com', 'bob@example.com'])
        alice = self.make_participant('alice', claimed_time='now')
        self.add_and_verify_email(alice, 'alice@example.com', 'bob@example.com')
        self.sign_in('alice')
        self.visit('/on/npm/foo/')
        self.css('label')[0].click()            # activate select
        self.css('label')[1].click()            # click second item
        self.css('li')[0].has_class('selected') # first item is still selected
        self.css('ul')[0].has_class('open')     # still open
        self.css('button').has_class('disabled')
        assert self.db.all('select * from claims') == []


    def test_that_claimed_packages_can_be_given_to(self):
        package = self.make_package()
        self.check()

        alice = P('alice')
        nonce = alice.get_email('alice@example.com').nonce
        alice.finish_email_verification('alice@example.com', nonce)

        self.make_participant('admin', claimed_time='now', is_admin=True)
        self.sign_in('admin')
        self.visit(package.team.url_path)
        self.css('#status-knob select').select('approved')
        self.css('#status-knob button').click()

        self.make_participant('bob', claimed_time='now')
        self.sign_in('bob')
        self.visit('/on/npm/foo/')

        self.css('.your-payment button.edit').click()
        self.wait_for('.your-payment input.amount').fill('10')
        self.css('.your-payment button.save').click()
        assert self.wait_for_success() == 'Payment changed to $10.00 per week. ' \
                                          'Thank you so much for supporting foo!'


    def test_visiting_verify_link_shows_helpful_information(self):
        self.make_package()
        self.check()

        link = pickle.loads(self.db.one('select context from email_queue'))['link']
        link = link[len(self.base_url):]  # strip because visit will add it back

        self.visit(link)
        assert self.css('.withdrawal-notice a').text == 'update'
        assert self.css('.withdrawal-notice b').text == 'alice@example.com'
        assert self.css('.listing-name').text == 'foo'
