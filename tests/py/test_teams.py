from __future__ import unicode_literals
from gratipay.models._mixin_team import StubParticipantAdded

from gratipay.testing import Harness
from gratipay.security.user import User
from gratipay.models.team import Team


class TestNewTeams(Harness):

    valid_data = {
        'name': 'Gratiteam',
        'homepage': 'http://gratipay.com/',
        'agree_terms': 'true',
        'product_or_service': 'Sample Product',
        'getting_paid': 'Getting Paid',
        'getting_involved': 'Getting Involved'
    }

    def post_new(self, data, auth_as='alice', expected=200):
        r =  self.client.POST('/teams/create.json', data=data, auth_as=auth_as, raise_immediately=False)
        assert r.code == expected
        return r

    def test_harness_can_make_a_team(self):
        team = self.make_team()
        assert team.name == 'The A Team'
        assert team.owner == 'hannibal'

    def test_can_construct_from_slug(self):
        self.make_team()
        team = Team.from_slug('TheATeam')
        assert team.name == 'The A Team'
        assert team.owner == 'hannibal'

    def test_can_construct_from_id(self):
        team = Team.from_id(self.make_team().id)
        assert team.name == 'The A Team'
        assert team.owner == 'hannibal'

    def test_can_create_new_team(self):
        self.make_participant('alice')
        self.post_new(self.valid_data)
        team = self.db.one("SELECT * FROM teams")
        assert team
        assert team.owner == 'alice'

    def test_401_for_anon_creating_new_team(self):
        self.post_new(self.valid_data, auth_as=None, expected=401)
        assert self.db.one("SELECT COUNT(*) FROM teams") == 0

    def test_error_message_for_terms(self):
        self.make_participant('alice')
        data = self.valid_data
        del data['agree_terms']
        r = self.post_new(data, expected=400)
        assert self.db.one("SELECT COUNT(*) FROM teams") == 0
        assert "Please agree to the terms and conditions" in r.body

    def test_error_message_for_missing_fields(self):
        self.make_participant('alice')
        data = self.valid_data
        del data['name']
        r = self.post_new(data, expected=400)
        assert self.db.one("SELECT COUNT(*) FROM teams") == 0
        assert "Please fill out the 'name' field" in r.body

class TestOldTeams(Harness):

    def setUp(self):
        Harness.setUp(self)
        self.team = self.make_participant('A-Team', number='plural')

    def test_is_team(self):
        expeted = True
        actual = self.team.IS_PLURAL
        assert actual == expeted

    def test_show_as_team_to_admin(self):
        self.make_participant('alice', is_admin=True)
        user = User.from_username('alice')
        assert self.team.show_as_team(user)

    def test_show_as_team_to_team_member(self):
        self.make_participant('alice')
        self.team.add_member(self.make_participant('bob', claimed_time='now'))
        user = User.from_username('bob')
        assert self.team.show_as_team(user)

    def test_show_as_team_to_non_team_member(self):
        self.make_participant('alice')
        self.team.add_member(self.make_participant('bob', claimed_time='now'))
        user = User.from_username('alice')
        assert self.team.show_as_team(user)

    def test_show_as_team_to_anon(self):
        self.make_participant('alice')
        self.team.add_member(self.make_participant('bob', claimed_time='now'))
        assert self.team.show_as_team(User())

    def test_dont_show_individuals_as_team(self):
        alice = self.make_participant('alice', number='singular')
        assert not alice.show_as_team(User())

    def test_dont_show_plural_no_members_as_team_to_anon(self):
        group = self.make_participant('Group', number='plural')
        assert not group.show_as_team(User())

    def test_dont_show_plural_no_members_as_team_to_auth(self):
        group = self.make_participant('Group', number='plural')
        self.make_participant('alice')
        assert not group.show_as_team(User.from_username('alice'))

    def test_show_plural_no_members_as_team_to_self(self):
        group = self.make_participant('Group', number='plural')
        assert group.show_as_team(User.from_username('Group'))

    def test_show_plural_no_members_as_team_to_admin(self):
        group = self.make_participant('Group', number='plural')
        self.make_participant('Admin', is_admin=True)
        assert group.show_as_team(User.from_username('Admin'))

    def test_can_add_members(self):
        alice = self.make_participant('alice', claimed_time='now')
        expected = True
        self.team.add_member(alice)
        actual = alice.member_of(self.team)
        assert actual == expected

    def test_get_teams_for_member(self):
        alice = self.make_participant('alice', claimed_time='now')
        bob = self.make_participant('bob', claimed_time='now')
        team = self.make_participant('B-Team', number='plural')
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
