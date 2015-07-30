from __future__ import unicode_literals

import pytest

from gratipay.testing import Harness
from gratipay.models.team import Team, AlreadyMigrated


class TestTeams(Harness):

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
        self.make_participant('alice', claimed_time='now', email_address='', last_paypal_result='')
        self.post_new(dict(self.valid_data))
        team = self.db.one("SELECT * FROM teams")
        assert team
        assert team.owner == 'alice'

    def test_all_fields_persist(self):
        self.make_participant('alice', claimed_time='now', email_address='', last_paypal_result='')
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
        self.make_participant('alice', claimed_time='now', email_address='alice@example.com', last_paypal_result='')
        data = dict(self.valid_data)
        del data['agree_terms']
        r = self.post_new(data, expected=400)
        assert self.db.one("SELECT COUNT(*) FROM teams") == 0
        assert "Please agree to the terms of service." in r.body

    def test_error_message_for_missing_fields(self):
        self.make_participant('alice', claimed_time='now', email_address='alice@example.com', last_paypal_result='')
        data = dict(self.valid_data)
        del data['name']
        r = self.post_new(data, expected=400)
        assert self.db.one("SELECT COUNT(*) FROM teams") == 0
        assert "Please fill out the 'Team Name' field." in r.body

    def test_error_message_for_slug_collision(self):
        self.make_participant('alice', claimed_time='now', email_address='alice@example.com', last_paypal_result='')
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
        self.make_participant('alice', claimed_time='now', email_address='alice@example.com', last_paypal_result='')
        data = dict(self.valid_data)
        data['name'] = "     "
        r = self.post_new(data, expected=400)
        assert self.db.one("SELECT COUNT(*) FROM teams") == 0
        assert "Please fill out the 'Team Name' field." in r.body

    def test_migrate_tips_to_payment_instructions(self):
        alice = self.make_participant('alice', claimed_time='now')
        bob = self.make_participant('bob', claimed_time='now')
        self.make_participant('old_team')
        alice.set_tip_to('old_team', '1.00')
        bob.set_tip_to('old_team', '2.00')
        new_team = self.make_team('new_team', owner='old_team')

        new_team.migrate_tips()

        payment_instructions = self.db.all("SELECT * FROM payment_instructions")
        assert len(payment_instructions) == 2
        assert payment_instructions[0].participant == 'alice'
        assert payment_instructions[0].team == 'new_team'
        assert payment_instructions[0].amount == 1
        assert payment_instructions[1].participant == 'bob'
        assert payment_instructions[1].team == 'new_team'
        assert payment_instructions[1].amount == 2

    def test_migrate_tips_only_runs_once(self):
        alice = self.make_participant('alice', claimed_time='now')
        self.make_participant('old_team')
        alice.set_tip_to('old_team', '1.00')
        new_team = self.make_team('new_team', owner='old_team')

        new_team.migrate_tips()

        with pytest.raises(AlreadyMigrated):
            new_team.migrate_tips()

        payment_instructions = self.db.all("SELECT * FROM payment_instructions")
        assert len(payment_instructions) == 1

    def test_migrate_tips_checks_for_multiple_teams(self):
        alice = self.make_participant('alice', claimed_time='now')
        self.make_participant('old_team')
        alice.set_tip_to('old_team', '1.00')
        new_team = self.make_team('new_team', owner='old_team')
        new_team.migrate_tips()

        newer_team = self.make_team('newer_team', owner='old_team')

        with pytest.raises(AlreadyMigrated):
            newer_team.migrate_tips()

        payment_instructions = self.db.all("SELECT * FROM payment_instructions")
        assert len(payment_instructions) == 1
