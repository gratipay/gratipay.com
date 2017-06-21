# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import pickle
from gratipay.testing import BrowserHarness, P
from gratipay.models.package import NPM, Package
from gratipay.models.participant import email


class Test(BrowserHarness):

    def check(self, choice=0):
        self.make_participant('alice', claimed_time='now')
        self.sign_in('alice')
        self.visit('/on/npm/foo/')
        self.css('#content label')[0].click() # activate select
        self.css('#content label')[choice].click()
        self.css('#content button')[0].click()
        address = ('alice' if choice == 0 else 'bob') + '@example.com'
        assert self.wait_for_success() == 'Check {} for a verification link.'.format(address)
        return self.db.one('select address from claims c join emails e on c.nonce = e.nonce')

    def finish_claiming(self):
        alice = P('alice')
        nonce = alice.get_email('alice@example.com').nonce
        return alice.finish_email_verification('alice@example.com', nonce)


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
        self.css('#content label')[0].click()            # activate select
        self.css('#content label')[1].click()            # click second item
        self.css('#content li')[0].has_class('selected') # first item is still selected
        self.css('#content ul')[0].has_class('open')     # still open
        self.css('#content button').has_class('disabled')
        assert self.db.all('select * from claims') == []


    def test_claimed_packages_can_be_given_to(self):
        package = self.make_package()
        self.check()
        self.finish_claiming()

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


    def test_deleted_packages_are_404(self):
        self.make_package()
        Package.from_names(NPM, 'foo').delete()
        self.visit('/on/npm/foo/')
        assert self.css('#content h1').text == '404'


    def test_claiming_deleted_packages_is_a_noop(self):
        self.make_package()
        self.check()
        Package.from_names(NPM, 'foo').delete()
        assert self.finish_claiming() == (email.VERIFICATION_SUCCEEDED, [], None)


    def test_but_once_claimed_then_team_persists(self):
        self.make_package()
        self.check()
        foo = Package.from_names(NPM, 'foo')
        assert self.finish_claiming() == (email.VERIFICATION_SUCCEEDED, [foo], True)
        foo.delete()
        self.visit('/foo/')
        foo = self.css('#content .statement p')
        assert foo.text == 'Foo fooingly.'


    def test_jdorfman_can_merge_accounts(self):
        jdorfman = self.make_participant('jdorfman', claimed_time='now', elsewhere='twitter')
        deadbeef = self.make_participant('deadbeef', claimed_time='now', elsewhere='github',
                                                                             last_paypal_result='')
        self.make_package(NPM, 'shml', claimed_by=deadbeef)

        github = deadbeef.get_account_elsewhere('github')
        token, _ = github.make_connect_token()
        self._browser.cookies.add({'connect_{}'.format(github.id): token})

        # jdorfman has nothing much right yet
        self.sign_in('jdorfman')
        self.visit('/~jdorfman/')
        assert len(self.css('.projects .listing tr')) == 0
        assert len(self.css('.accounts tr.has-avatar')) == 1
        self.visit('/~jdorfman/routes/')
        assert self.css('.account-details span').text == ''

        # jdorfman can take over deadbeef
        self.visit('/on/confirm.html?id={}'.format(github.id))
        self.css('button[value=yes]').click()
        assert len(self.css('.projects .listing tr')) == 1
        assert len(self.css('.accounts tr.has-avatar')) == 2
        self.visit('/~jdorfman/routes/')
        assert self.css('.account-details span').text == 'abcd@gmail.com'

        # admin can browse event
        self.sign_in('admin')
        self.visit('/~jdorfman/events/')
        payload = eval(self.css('table#events td.payload').text)
        assert payload['action'] == 'take-over'
        assert payload['values']['exchange_routes'] == [r.id for r in jdorfman.get_payout_routes()]


class BulkClaiming(BrowserHarness):

    def setUp(self):
        self.make_package()
        self.make_package( name='bar'
                         , description='Bar barringly'
                         , emails=['alice@example.com', 'bob@example.com']
                          )
        self.make_package( name='baz'
                         , description='Baz bazzingly'
                         , emails=['alice@example.com', 'bob@example.com', 'cat@example.com']
                          )

    def visit_as(self, username):
        self.visit('/')
        self.sign_in(username)
        self.visit('/on/npm/?flow=receive')

    def test_anon_gets_sign_in_prompt(self):
        self.visit('/on/npm/?flow=receive')
        assert self.css('.important-button button').text == 'Sign in / Sign up'

    def test_auth_without_email_gets_highlighted_link_to_email(self):
        self.make_participant('alice', claimed_time='now')
        self.visit_as('alice')
        assert self.css('.highlight').text == 'Link an email'

    def test_auth_without_claimable_packages_gets_disabled_apply_button(self):
        self.make_participant('doug', claimed_time='now', email_address='doug@example.com')
        self.visit_as('doug')
        button = self.css('.important-button button')
        assert button.text == 'Apply to accept payments'
        assert button['disabled'] == 'true'

    def test_auth_with_claimable_packages_gets_apply_button(self):
        self.make_participant('alice', claimed_time='now', email_address='alice@example.com')
        self.add_and_verify_email('alice', 'bob@example.com')
        self.visit_as('alice')
        button = self.css('.important-button button')
        assert button.text == 'Apply to accept payments'
        assert button['disabled'] is None

    def test_differentiates_claimed_packages(self):
        self.make_participant('bob', claimed_time='now', email_address='bob@example.com')
        self.make_participant('alice', claimed_time='now', email_address='alice@example.com')
        self.claim_package('alice', 'foo')
        self.claim_package('bob', 'bar')
        self.visit_as('alice')
        assert self.css('.i1').has_class('disabled')
        assert self.css('.i1 .owner a').text == '~bob'
        assert not self.css('.i2').has_class('disabled')
        assert self.css('.i3').has_class('disabled')
        assert self.css('.i3 .owner a').text == 'you'

    def test_sends_mail(self):
        self.make_participant('cat', claimed_time='now', email_address='cat@example.com')
        self.visit_as('cat')
        self.css('.important-button button').click()
        assert self.wait_for_success() == 'Check cat@example.com for a verification link.'

    def test_sends_one_mail_per_address(self):
        cat = self.make_participant('cat', claimed_time='now', email_address='cat@example.com')
        self.add_and_verify_email(cat, 'bob@example.com')
        self.visit_as('cat')
        self.css('.important-button button').click()
        assert self.wait_for_success('Check bob@example.com for a verification link.')
        assert self.wait_for_success('Check cat@example.com for a verification link.')

    def test_sends_one_mail_for_multiple_packages(self):
        self.make_participant('alice', claimed_time='now', email_address='alice@example.com')
        self.visit_as('alice')
        self.css('.important-button button').click()
        assert len(self.css('table.listing td.item')) == 3
        assert self.wait_for_success() == 'Check alice@example.com for a verification link.'
        assert self.db.one('select count(*) from claims') == 3
        assert self.db.one('select count(*) from email_queue') == 1

    def test_doesnt_send_for_unclaimable_packages(self):
        self.make_participant('alice', claimed_time='now', email_address='alice@example.com')
        self.make_participant('cat', claimed_time='now', email_address='cat@example.com')
        self.claim_package('cat', 'baz')
        self.visit_as('alice')
        self.css('.important-button button').click()
        assert len(self.css('table.listing td.item')) == 3
        assert self.wait_for_success() == 'Check alice@example.com for a verification link.'
        assert self.db.one('select count(*) from claims') == 2
        assert self.db.one('select count(*) from email_queue') == 1
