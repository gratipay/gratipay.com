from __future__ import unicode_literals

from gratipay.models.team import StubParticipantAdded
from gratipay.testing import Harness


class Tests(Harness):

    def setUp(self):
        Harness.setUp(self)
        self.owner = self.make_participant('hannibal')
        self.team = self.make_team('A-Team', self.owner.username)

    def test_can_add_members(self):
        alice = self.make_participant('alice', claimed_time='now')
        self.team.add_member(alice)
        assert alice.member_of(self.team)

    def test_get_teams_for_member(self):
        alice = self.make_participant('alice', claimed_time='now')
        bob = self.make_participant('bob', claimed_time='now')
        carl = self.make_participant('carl', claimed_time='now')
        team = self.make_team('B-Team', carl.username)
        self.team.add_member(alice)
        team.add_member(bob)
        expected = 1
        actual = alice.get_teams().pop().nmembers
        assert actual == expected

    def test_preclude_adding_stub_participant(self):
        stub_participant = self.make_participant('stub')
        with self.assertRaises(StubParticipantAdded):
            self.team.add_member(stub_participant)

    def test_remove_all_members(self):
        alice = self.make_participant('alice', claimed_time='now')
        self.team.add_member(alice)
        bob = self.make_participant('bob', claimed_time='now')
        self.team.add_member(bob)

        assert len(self.team.get_current_takes()) == 2  # sanity check
        self.team.remove_all_members()
        assert len(self.team.get_current_takes()) == 0
