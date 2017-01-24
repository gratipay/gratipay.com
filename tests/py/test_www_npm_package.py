# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

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
        assert 'with one of these email addresses' in body
