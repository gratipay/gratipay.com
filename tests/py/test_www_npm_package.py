# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.models.package import NPM, Package
from gratipay.testing import Harness


class Tests(Harness):

    def setUp(self):
        self.make_package()

    def test_trailing_slash_redirects(self):
        response = self.client.GxT('/on/npm/foo/')
        assert response.code == 302
        assert response.headers['Location'] == '/on/npm/foo'

    def test_anon_gets_signin_page_from_unclaimed(self):
        body = self.client.GET('/on/npm/foo').body
        assert 'foo</a> npm package on Gratipay:' in body

    def test_auth_gets_send_confirmation_page_from_unclaimed(self):
        self.make_participant('bob', claimed_time='now')
        body = self.client.GET('/on/npm/foo', auth_as='bob').body
        assert 'foo</a> npm package:' in body
        assert 'alice@example.com' in body

    def test_auth_gets_multiple_options_if_present(self):
        self.make_package(NPM, 'bar', 'Bar', ['alice@example.com', 'alice@example.net'])
        self.make_participant('bob', claimed_time='now')
        body = self.client.GET('/on/npm/bar', auth_as='bob').body
        assert 'alice@example.com' in body
        assert 'alice@example.net' in body

    def test_auth_gets_something_if_no_emails(self):
        self.make_package(NPM, 'bar', 'Bar', [])
        self.make_participant('bob', claimed_time='now')
        body = self.client.GET('/on/npm/bar', auth_as='bob').body
        assert "No email addresses on file" in body


    def claim_package(self):
        foo = Package.from_names('npm', 'foo')
        alice = self.make_participant('alice', claimed_time='now')
        alice.start_email_verification('alice@example.com', foo)
        nonce = alice.get_email('alice@example.com').nonce
        alice.finish_email_verification('alice@example.com', nonce)
        team = alice.get_teams()[0]
        assert team.package == foo
        return team.slug

    def test_package_redirects_to_project_if_claimed(self):
        self.claim_package()
        response = self.client.GxT('/on/npm/foo')
        assert response.code == 302
        assert response.headers['Location'] == '/foo/'

    def test_package_served_as_project_if_claimed(self):
        self.claim_package()
        assert 'owned by' in self.client.GET('/foo/').body


class Bulk(Harness):

    def setUp(self):
        self.make_package()

    def test_anon_gets_payment_flow(self):
        body = self.client.GET('/on/npm/').body
        assert 'Paste a package.json' in body
        assert '0 out of all 1 npm package' in body
