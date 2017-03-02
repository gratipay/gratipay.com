# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing.billing import BillingHarness


class TestNMassPays(BillingHarness):

    def setUp(self):
        BillingHarness.setUp(self)
        self.make_participant('admin', claimed_time='now', is_admin=True).username
        team = self.make_team(owner=self.homer, is_approved=True)
        self.obama.set_payment_instruction(team, '20.00')

    def post_masspays(self, n):
        for i in range(n):
            self.client.PxST( '/~homer/history/record-an-exchange'
                            , { 'amount': '-20'
                              , 'fee': '0'
                              , 'note': 'Exchange!'
                              , 'status': 'succeeded'
                              , 'route_id': unicode(self.homer_route.id)
                               }
                            , auth_as='admin'
                             )  # responds with 302


    def test_returns_zero_for_no_paydays(self):
        assert self.client.GET('/dashboard/nmasspays').body == '0'

    def test_returns_zero_for_one_payday(self):
        self.run_payday()
        assert self.client.GET('/dashboard/nmasspays').body == '0'

    def test_returns_zero_for_penultimate_payday_with_no_masspays(self):
        self.run_payday(); self.post_masspays(2)
        self.run_payday()
        self.run_payday(); self.post_masspays(1)
        assert self.client.GET('/dashboard/nmasspays').body == '0'

    def test_returns_three_for_penultimate_payday_with_three_masspays(self):
        self.run_payday(); self.post_masspays(1)
        self.run_payday(); self.post_masspays(4)
        self.run_payday(); self.post_masspays(2)
        self.run_payday(); self.post_masspays(3)
        self.run_payday(); self.post_masspays(8)
        assert self.client.GET('/dashboard/nmasspays').body == '3'
