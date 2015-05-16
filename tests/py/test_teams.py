from __future__ import unicode_literals

from decimal import Decimal

from gratipay.models.team import StubParticipantAdded
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
        self.make_participant('alice', claimed_time='now', email_address='', last_ach_result='')
        self.post_new(dict(self.valid_data))
        team = self.db.one("SELECT * FROM teams")
        assert team
        assert team.owner == 'alice'

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

    def test_can_add_members(self):
        alice = self.make_participant('alice', claimed_time='now')
        team = self.make_team()
        team.add_member(alice)
        assert alice.member_of(team) == True

    def test_get_teams_for_member(self):
        alice = self.make_participant('alice', claimed_time='now')
        bob = self.make_participant('bob', claimed_time='now')
        team = self.make_team()
        team.add_member(alice)
        team.add_member(bob)

        alice_teams = alice.get_teams()
        assert len(alice_teams) == 1
        assert alice_teams[0].nmembers == 2

    def test_preclude_adding_stub_participant(self):
        team = self.make_team()
        stub_participant = self.make_participant('stub')
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

    # receiving, nsupporters and payroll

    def test_only_funded_subscriptions_count(self):
        alice = self.make_participant('alice', claimed_time='now', last_bill_result='')
        bob = self.make_participant('bob', claimed_time='now')
        carl = self.make_participant('carl', claimed_time='now', last_bill_result="Fail!")
        team = self.make_team(is_approved=True)

        alice.set_subscription_to(team, '3.00') # The only funded tip
        bob.set_subscription_to(team, '5.00')
        carl.set_subscription_to(team, '7.00')

        assert team.receiving == Decimal('3.00')
        assert team.nsupporters == 1

        funded_tip = self.db.one("SELECT * FROM subscriptions WHERE is_funded ORDER BY id")
        assert funded_tip.subscriber == alice.username

    def test_receiving_includes_tips_from_whitelisted_accounts(self):
        alice = self.make_participant( 'alice'
                                     , claimed_time='now'
                                     , last_bill_result=''
                                     , is_suspicious=False
                                      )
        team = self.make_team(is_approved=True)
        alice.set_subscription_to(team, '3.00')

        assert team.receiving == Decimal('3.00')
        assert team.nsupporters == 1

    def test_receiving_includes_tips_from_unreviewed_accounts(self):
        alice = self.make_participant( 'alice'
                                     , claimed_time='now'
                                     , last_bill_result=''
                                     , is_suspicious=None
                                      )
        team = self.make_team(is_approved=True)
        alice.set_subscription_to(team, '3.00')

        assert team.receiving == Decimal('3.00')
        assert team.nsupporters == 1

    def test_receiving_ignores_tips_from_blacklisted_accounts(self):
        alice = self.make_participant( 'alice'
                                     , claimed_time='now'
                                     , last_bill_result=''
                                     , is_suspicious=True
                                      )
        team = self.make_team(is_approved=True)
        alice.set_subscription_to(team, '3.00')

        assert team.receiving == Decimal('0.00')
        assert team.nsupporters == 0

class TestOldTeams(Harness):

    def setUp(self):
        Harness.setUp(self)
        self.team = self.make_participant('A-Team', number='plural')

    def test_is_team(self):
        expeted = True
        actual = self.team.IS_PLURAL
        assert actual == expeted

    def test_show_as_team_always_returns_false(self):
        self.make_participant('alice', is_admin=True)
        user = User.from_username('alice')
        assert self.team.show_as_team(user) == False


