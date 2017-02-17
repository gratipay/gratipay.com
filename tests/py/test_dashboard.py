# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing.billing import BillingHarness


class TestNMassPays(BillingHarness):

    # nmp - nmasspays

    def setUp(self):
        BillingHarness.setUp(self)
        self.make_participant('admin', claimed_time='now', is_admin=True).username

    def post_masspay(self, username, route, amount):
        self.client.PxST( '/~{}/history/record-an-exchange'.format(username)
                        , { 'amount': unicode(amount)
                          , 'fee': '0'
                          , 'note': 'Exchange!'
                          , 'status': 'succeeded'
                          , 'route_id': unicode(route.id)
                           }
                        , auth_as='admin'
                         )  # responds with 302


    def test_nmp_returns_zero_for_no_paydays(self):
        self.client.GET('/dashboard/nmasspays').body == '0'

    def test_nmp_returns_zero_for_no_masspays(self):
        self.run_payday()
        self.client.GET('/dashboard/nmasspays').body == '0'

    def test_nmp_returns_one_for_one_payday_with_one_masspay(self):
        team = self.make_team(owner=self.homer, is_approved=True)
        self.obama.set_payment_instruction(team, '20.00')
        self.run_payday()
        self.post_masspay('homer', self.homer_route, 20)
        self.client.GET('/dashboard/nmasspays').body == '1'

    def test_nmp_returns_one_for_many_paydays_with_one_masspay(self):
        team = self.make_team(owner=self.homer, is_approved=True)
        self.obama.set_payment_instruction(team, '20.00')
        for i in range(10):
            self.run_payday()
            self.post_masspay('homer', self.homer_route, 20)
        self.client.GET('/dashboard/nmasspays').body == '1'
