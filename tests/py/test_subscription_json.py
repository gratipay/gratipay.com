from __future__ import print_function, unicode_literals

import json

from aspen.utils import utcnow
from gratipay.testing import Harness


class TestTipJson(Harness):

    def test_api_returns_amount_and_totals(self):
        "Test that we get correct amounts and totals back on POSTs to subscription.json"

        # First, create some test data
        # We need accounts
        now = utcnow()
        self.make_team("A", is_approved=True)
        self.make_team("B", is_approved=True)
        self.make_participant("alice", claimed_time=now, last_bill_result='')

        # Then, add a $1.50 and $3.00 subscription
        response1 = self.client.POST( "/A/subscription.json"
                                    , {'amount': "1.50"}
                                    , auth_as='alice'
                                     )

        response2 = self.client.POST( "/B/subscription.json"
                                    , {'amount': "3.00"}
                                    , auth_as='alice'
                                     )

        # Confirm we get back the right amounts.
        first_data = json.loads(response1.body)
        second_data = json.loads(response2.body)
        assert first_data['amount'] == "1.50"
        assert second_data['amount'] == "3.00"

        # Bring these back when cached values are updated
        # assert first_data['total_giving'] == "1.50"
        # assert second_data['total_giving'] == "4.50"


    def test_setting_subscription_out_of_range_gets_bad_amount(self):
        self.make_team(is_approved=True)
        self.make_participant("alice", claimed_time='now', last_bill_result='')

        response = self.client.PxST( "/TheATeam/subscription.json"
                                   , {'amount': "1010.00"}
                                   , auth_as='alice'
                                    )
        assert "bad amount" in response.body
        assert response.code == 400

        response = self.client.PxST( "/TheATeam/subscription.json"
                                   , {'amount': "-1.00"}
                                   , auth_as='alice'
                                    )
        assert "bad amount" in response.body
        assert response.code == 400


    def test_subscribing_to_rejected_team_fails(self):
        self.make_team(is_approved=False)
        self.make_participant("alice", claimed_time='now', last_bill_result='')
        response = self.client.PxST( "/TheATeam/subscription.json"
                                   , {'amount': "10.00"}
                                   , auth_as='alice'
                                    )
        assert "unapproved team" in response.body
        assert response.code == 400
