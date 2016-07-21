from __future__ import print_function, unicode_literals

from gratipay.testing import Harness, P

workflow = ['too-little', 'pending-application', 'pending-review', 'rejected', 'pending-payout',
            'completed']


class Tests(Harness):
    def setUp(self):
        super(Harness)
        self.make_participant('alice', claimed_time='now', last_paypal_result='')
        self.make_participant('admin', claimed_time='now', is_admin=True)

    def hit(self, new_status, expecting_error=True, auth_as='admin'):
        method = self.client.PxST if expecting_error else self.client.POST
        return method("/~alice/payout-status", {'to': new_status}, auth_as=auth_as)

    def test_admin_can_change_status(self):
        for status in workflow:
            response = self.hit(status, expecting_error=False)
            assert response.code == 200
            assert P('alice').status_of_1_0_payout == status

    def test_user_cant_change_status_except_for_applying(self):
        self.db.run("UPDATE participants SET status_of_1_0_payout='pending-application' "
                    "WHERE username='alice'")

        response = self.hit('pending-payout', auth_as='alice')
        assert response.code == 403
        assert P('alice').status_of_1_0_payout == 'pending-application'

        response = self.hit('pending-review', auth_as='alice', expecting_error=False)
        assert P('alice').status_of_1_0_payout == 'pending-review'

    def test_user_must_have_a_payout_route(self):
        self.db.run("DELETE FROM exchange_routes;")
        response = self.hit('pending-payout', auth_as='admin')
        assert response.code == 400
        assert P('alice').status_of_1_0_payout == 'completed'

    def test_invalid_is_400(self):
        response = self.hit('invalid_status')
        assert response.code == 400

    def test_can_update_status_via_trigger_on_participant_balance(self):
        self.db.run("UPDATE participants "
                    "SET balance=10, status_of_1_0_payout='pending-application' "
                    "WHERE username='alice'")
        alice = P('alice')
        assert alice.balance == 10
        assert alice.status_of_1_0_payout == 'pending-application';

        self.db.run("UPDATE participants SET balance=0 WHERE username='alice'")
        alice = P('alice')
        assert alice.balance == 0
        assert alice.status_of_1_0_payout == 'completed';
