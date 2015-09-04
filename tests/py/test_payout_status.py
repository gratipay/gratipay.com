from __future__ import print_function, unicode_literals

from gratipay.testing import Harness
from gratipay.models.participant import Participant

workflow = ['pending-application', 'pending-review', 'rejected', 'pending-payout', 'completed']


class Tests(Harness):
    def setUp(self):
        super(Harness)
        self.make_participant('alice', claimed_time='now')
        self.make_participant('admin', claimed_time='now', is_admin=True)

    def hit(self, new_status, auth_as='admin'):
        return self.client.PxST(
            "/~alice/payout-status",
            {'to': new_status},
            auth_as=auth_as
        )

    def test_admin_can_change_status(self):
        for status in workflow:
            response = self.hit(status)
            assert response.code == 302
            assert Participant.from_username('alice').status_of_1_0_payout == status

    def test_user_cant_change_status(self):
        response = self.hit('pending-payout', auth_as='alice')
        assert response.code == 401
        assert Participant.from_username('alice').status_of_1_0_payout == 'completed'

    def test_invalid_is_400(self):
        response = self.hit('invalid_status')
        assert response.code == 400
