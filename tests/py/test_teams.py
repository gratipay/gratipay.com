from __future__ import unicode_literals

from gratipay.models.team import StubParticipantAdded
from gratipay.testing import Harness


class Tests(Harness):

    def test_can_add_members(self):
        team = self.make_team()
        alice = self.make_participant('alice', claimed_time='now')
        team.add_member(alice)
        assert alice.member_of(team)

    def test_get_teams_gets_teams(self):
        alice = self.make_participant('alice', claimed_time='now')
        bob = self.make_participant('bob', claimed_time='now')
        a = self.make_team()
        carl = self.make_participant('carl', claimed_time='now')
        b = self.make_team('The B Team', carl.username)
        a.add_member(alice)
        a.add_member(bob)
        b.add_member(bob)
        assert [t.display_name for t in alice.get_teams()] == ['The A Team']
        assert [t.slug for t in bob.get_teams()] == ['TheATeam', 'TheBTeam']

    def test_preclude_adding_stub_participant(self):
        stub_participant = self.make_participant('stub')
        team = self.make_team()
        with self.assertRaises(StubParticipantAdded):
            team.add_member(stub_participant)

    def test_remove_all_members(self):
        team = self.make_team()
        alice = self.make_participant('alice', claimed_time='now')
        team.add_member(alice)
        bob = self.make_participant('bob', claimed_time='now')
        team.add_member(bob)

        assert len(team.get_current_takes()) == 2  # sanity check
        team.remove_all_members()
        assert len(team.get_current_takes()) == 0
