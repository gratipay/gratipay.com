from __future__ import print_function, unicode_literals

import json

from gratipay.testing import Harness, D, T


class TestPaymentInstructionJson(Harness):

    def test_api_returns_amount_and_totals(self):
        "Test that we get correct amounts and totals back on POSTs to payment-instruction.json"

        # First, create some test data
        # We need accounts
        self.make_team("A", is_approved=True)
        self.make_team("B", is_approved=True)
        self.make_participant("alice", claimed_time='now', last_bill_result='')

        # Then, add a $1.50 and $3.00 payment instruction
        response1 = self.client.POST( "/A/payment-instruction.json"
                                    , {'amount': "1.50"}
                                    , auth_as='alice'
                                     )

        response2 = self.client.POST( "/B/payment-instruction.json"
                                    , {'amount': "3.00"}
                                    , auth_as='alice'
                                     )

        # Confirm we get back the right amounts.
        first_data = json.loads(response1.body)
        second_data = json.loads(response2.body)
        assert first_data['amount'] == "1.50"
        assert second_data['amount'] == "3.00"

        # Bring these back when cached values are updated
        assert first_data['total_giving'] == "1.50"
        assert second_data['total_giving'] == "4.50"


    def test_setting_payment_instruction_out_of_range_gets_bad_amount(self):
        self.make_team(is_approved=True)
        self.make_participant("alice", claimed_time='now', last_bill_result='')

        response = self.client.PxST( "/TheEnterprise/payment-instruction.json"
                                   , {'amount': "1010.00"}
                                   , auth_as='alice'
                                    )
        assert "bad amount" in response.body
        assert response.code == 400

        response = self.client.PxST( "/TheEnterprise/payment-instruction.json"
                                   , {'amount': "-1.00"}
                                   , auth_as='alice'
                                    )
        assert "bad amount" in response.body
        assert response.code == 400


    def test_subscribing_to_rejected_team_fails(self):
        self.make_team(is_approved=False)
        self.make_participant("alice", claimed_time='now', last_bill_result='')
        response = self.client.PxST( "/TheEnterprise/payment-instruction.json"
                                   , {'amount': "10.00"}
                                   , auth_as='alice'
                                    )
        assert "unapproved team" in response.body
        assert response.code == 400


    def check_parsing(self, lang, amount):
        alice = self.make_participant('alice', claimed_time='now', last_bill_result='')
        self.make_team(is_approved=True)
        self.client.POST( '/TheEnterprise/payment-instruction.json'
                        , data={'amount': amount}
                        , auth_as='alice'
                        , HTTP_ACCEPT_LANGUAGE=str(lang)
                         )
        assert alice.get_payment_instruction(T('TheEnterprise'))['amount'] == D('0.05')

    def test_amount_is_parsed_as_expected_in_english(self):
        self.check_parsing('en', '0.05')

    def test_amount_is_parsed_as_expected_in_italian(self):
        self.check_parsing('it', '0,05')
