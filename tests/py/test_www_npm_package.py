# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.models.package import NPM
from gratipay.testing import Harness


class TestClaimingWorkflow(Harness):

    def setUp(self):
        self.make_package()

    def test_anon_gets_signin_page_from_unclaimed(self):
        body = self.client.GET('/on/npm/foo/').body
        assert 'npm/foo</a> has not been claimed' in body
        assert 'with a couple clicks' in body

    def test_auth_gets_send_confirmation_page_from_unclaimed(self):
        self.make_participant('bob', claimed_time='now')
        body = self.client.GET('/on/npm/foo/', auth_as='bob').body
        assert 'npm/foo</a> has not been claimed' in body
        assert 'using any email address' in body
        assert 'alice@example.com' in body

    def test_auth_gets_multiple_options_if_present(self):
        self.make_package(NPM, 'bar', 'Bar', ['alice@example.com', 'alice@example.net'])
        self.make_participant('bob', claimed_time='now')
        body = self.client.GET('/on/npm/bar/', auth_as='bob').body
        assert 'using any email address' in body
        assert 'alice@example.com' in body
        assert 'alice@example.net' in body

    def test_auth_gets_something_if_no_emails(self):
        self.make_package(NPM, 'bar', 'Bar', [])
        self.make_participant('bob', claimed_time='now')
        body = self.client.GET('/on/npm/bar/', auth_as='bob').body
        assert "didn&#39;t find any email addresses" in body
