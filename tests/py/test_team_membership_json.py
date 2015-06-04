from __future__ import print_function, unicode_literals

from gratipay.testing import Harness


class Tests(Harness):

    def hit(self, team, action, auth_as='alice', expected_code=200):
        method = self.client.POST if expected_code == 200 else self.client.PxST
        response = method(
            "/~alice/team-membership.json",
            {'team': team, 'action': action},
            auth_as=auth_as
        )
        assert response.code == expected_code
        return response

    def test_error_for_invalid_team_slug(self):
        self.make_participant('alice', claimed_time='now')
        response = self.hit('a-team', 'accept', expected_code=400)
        assert "Team doesn't exist" in response.body

    def test_error_for_invalid_action(self):
        self.make_participant('alice', claimed_time='now')
        self.make_team('a-team')
        response = self.hit('a-team', 'test', expected_code=400)
        assert "Action should be either accept or decline" in response.body

    def test_participant_can_accept_invitation(self):
        alice = self.make_participant('alice', claimed_time='now')
        team = self.make_team('a-team')
        team.add_member(alice)
        self.hit('a-team', 'accept')
        actual = self.db.one("SELECT is_active FROM team_memberships WHERE member='alice' AND team='a-team'")
        assert actual == True

    def test_participant_can_decline_invitation(self):
        alice = self.make_participant('alice', claimed_time='now')
        team = self.make_team('a-team')
        team.add_member(alice)
        self.hit('a-team', 'decline')
        actual = self.db.one("SELECT is_active FROM team_memberships WHERE member='alice' AND team='a-team'")
        assert actual == False
