from __future__ import unicode_literals

import pytest

from gratipay.models._mixin_team import StubParticipantAdded
from gratipay.testing import Harness
from gratipay.security.user import User
from gratipay.models.team import Team, AlreadyMigrated


class TestNewTeams(Harness):

    valid_data = {
        'name': 'Gratiteam',
        'homepage': 'http://gratipay.com/',
        'agree_terms': 'true',
        'product_or_service': 'We make widgets.',
        'revenue_model': 'People pay us.',
        'getting_involved': 'People do stuff.',
        'getting_paid': 'We pay people.'
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
        self.make_participant('alice', claimed_time='now', email_address='', last_ach_result='')
        self.post_new(dict(self.valid_data))
        team = self.db.one("SELECT * FROM teams")
        assert team
        assert team.owner == 'alice'

    def test_all_fields_persist(self):
        self.make_participant('alice', claimed_time='now', email_address='', last_ach_result='')
        self.post_new(dict(self.valid_data))
        team = Team.from_slug('gratiteam')
        assert team.name == 'Gratiteam'
        assert team.homepage == 'http://gratipay.com/'
        assert team.product_or_service == 'We make widgets.'
        assert team.revenue_model == 'People pay us.'
        assert team.getting_involved == 'People do stuff.'
        assert team.getting_paid == 'We pay people.'

    def test_401_for_anon_creating_new_team(self):
        self.post_new(self.valid_data, auth_as=None, expected=401)
        assert self.db.one("SELECT COUNT(*) FROM teams") == 0

    def test_error_message_for_no_valid_email(self):
        self.make_participant('alice', claimed_time='now')
        r = self.post_new(dict(self.valid_data), expected=400)
        assert self.db.one("SELECT COUNT(*) FROM teams") == 0
        assert "You must have a verified email address to apply for a new team." in r.body

    def test_error_message_for_no_payout_route(self):
        self.make_participant('alice', claimed_time='now', email_address='alice@example.com')
        r = self.post_new(dict(self.valid_data), expected=400)
        assert self.db.one("SELECT COUNT(*) FROM teams") == 0
        assert "You must attach a bank account or PayPal to apply for a new team." in r.body

    def test_error_message_for_terms(self):
        self.make_participant('alice', claimed_time='now', email_address='alice@example.com', last_ach_result='')
        data = dict(self.valid_data)
        del data['agree_terms']
        r = self.post_new(data, expected=400)
        assert self.db.one("SELECT COUNT(*) FROM teams") == 0
        assert "Please agree to the terms of service." in r.body

    def test_error_message_for_missing_fields(self):
        self.make_participant('alice', claimed_time='now', email_address='alice@example.com', last_ach_result='')
        data = dict(self.valid_data)
        del data['name']
        r = self.post_new(data, expected=400)
        assert self.db.one("SELECT COUNT(*) FROM teams") == 0
        assert "Please fill out the 'Team Name' field." in r.body

    def test_error_message_for_slug_collision(self):
        self.make_participant('alice', claimed_time='now', email_address='alice@example.com', last_ach_result='')
        self.post_new(dict(self.valid_data))
        r = self.post_new(dict(self.valid_data), expected=400)
        assert self.db.one("SELECT COUNT(*) FROM teams") == 1
        assert "Sorry, there is already a team using 'gratiteam'." in r.body

    def test_approved_team_shows_up_on_explore_teams(self):
        self.make_team(is_approved=True)
        assert 'The A Team' in self.client.GET("/explore/teams/").body

    def test_unreviewed_team_does_not_show_up_on_explore_teams(self):
        self.make_team(is_approved=None)
        assert 'The A Team' not in self.client.GET("/explore/teams/").body

    def test_rejected_team_does_not_show_up_on_explore_teams(self):
        self.make_team(is_approved=False)
        assert 'The A Team' not in self.client.GET("/explore/teams/").body

    def test_stripping_required_inputs(self):
        self.make_participant('alice', claimed_time='now', email_address='alice@example.com', last_ach_result='')
        data = dict(self.valid_data)
        data['name'] = "     "
        r = self.post_new(data, expected=400)
        assert self.db.one("SELECT COUNT(*) FROM teams") == 0
        assert "Please fill out the 'Team Name' field." in r.body

    def test_migrate_tips_to_subscriptions(self):
        alice = self.make_participant('alice', claimed_time='now')
        bob = self.make_participant('bob', claimed_time='now')
        self.make_participant('old_team')
        alice.set_tip_to('old_team', '1.00')
        bob.set_tip_to('old_team', '2.00')
        new_team = self.make_team('new_team', owner='old_team')

        new_team.migrate_tips()

        subscriptions = self.db.all("SELECT * FROM subscriptions")
        assert len(subscriptions) == 2
        assert subscriptions[0].subscriber == 'alice'
        assert subscriptions[0].team == 'new_team'
        assert subscriptions[0].amount == 1
        assert subscriptions[1].subscriber == 'bob'
        assert subscriptions[1].team == 'new_team'
        assert subscriptions[1].amount == 2

    def test_migrate_tips_only_runs_once(self):
        alice = self.make_participant('alice', claimed_time='now')
        self.make_participant('old_team')
        alice.set_tip_to('old_team', '1.00')
        new_team = self.make_team('new_team', owner='old_team')

        self.db.run("""
            INSERT INTO subscriptions
                        (ctime, subscriber, team, amount)
                 VALUES (CURRENT_TIMESTAMP, 'alice', 'new_team', 1)
        """)

        with pytest.raises(AlreadyMigrated):
            new_team.migrate_tips()

        subscriptions = self.db.all("SELECT * FROM subscriptions")
        assert len(subscriptions) == 1

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

    def test_get_old_teams_for_member(self):
        alice = self.make_participant('alice', claimed_time='now')
        bob = self.make_participant('bob', claimed_time='now')
        team = self.make_participant('B-Team', number='plural')
        self.team.add_member(alice)
        team.add_member(bob)
        expected = 1
        actual = alice.get_old_teams().pop().nmembers
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
