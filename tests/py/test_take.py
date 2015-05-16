from __future__ import unicode_literals

from decimal import Decimal as D

from gratipay.testing import Harness
from gratipay.models.participant import Participant
from gratipay.models.team import Team


TEAM = 'A Team'


class Tests(Harness):

    def take_last_week(self, team, member, amount, actual_amount=None):
        team._Team__set_take_for(member, amount, member)
        self.db.run("INSERT INTO paydays DEFAULT VALUES")
        actual_amount = amount if actual_amount is None else actual_amount
        self.db.run("""
            INSERT INTO payments (team, participant, amount, direction)
                 VALUES (%s, %s, %s, 'to-participant')
        """, (team.slug, member.username, actual_amount))
        self.db.run("UPDATE paydays SET ts_end=now() WHERE ts_end < ts_start")

    def test_we_can_make_a_team(self):
        team = self.make_team()
        assert isinstance(team, Team)

    def test_random_schmoe_is_not_member_of_team(self):
        team = self.make_team()
        schmoe = self.make_participant('schmoe')
        assert not schmoe.member_of(team)

    def test_team_member_is_team_member(self):
        team = self.make_team()
        alice = self.make_participant('alice', claimed_time='now')
        self.take_last_week(team, alice, '40.00')
        assert alice.member_of(team)

    def test_cant_grow_tip_a_lot(self):
        team = self.make_team()
        alice = self.make_participant('alice', claimed_time='now')
        self.take_last_week(team, alice, '40.00')
        assert team.set_take_for(alice, D('100.00'), alice) == 80

    def test_take_can_double(self):
        team = self.make_team()
        alice = self.make_participant('alice', claimed_time='now')
        self.take_last_week(team, alice, '40.00')
        team.set_take_for(alice, D('80.00'), alice)
        assert team.get_take_for(alice) == 80

    def test_take_can_double_but_not_a_penny_more(self):
        team = self.make_team()
        alice = self.make_participant('alice', claimed_time='now')
        self.take_last_week(team, alice, '40.00')
        actual = team.set_take_for(alice, D('80.01'), alice)
        assert actual == 80

    def test_increase_is_based_on_nominal_take_last_week(self):
        team = self.make_team()
        alice = self.make_participant('alice', claimed_time='now')
        self.take_last_week(team, alice, '20.00', actual_amount='15.03')
        team._Team__set_take_for(alice, D('35.00'), team.owner)
        assert team.set_take_for(alice, D('42.00'), alice) == 40

    def test_if_last_week_is_less_than_a_dollar_can_increase_to_a_dollar(self):
        team = self.make_team()
        alice = self.make_participant('alice', claimed_time='now')
        self.take_last_week(team, alice, '0.01')
        actual = team.set_take_for(alice, D('42.00'), team.owner)
        assert actual == 1

    def test_get_members(self):
        team = self.make_team()

        # TODO - Change this to create a subscription after update_receiving is fixed.
        self.db.run("UPDATE teams SET receiving='100' WHERE slug=%s", (team.slug,))
        team = Team.from_slug(team.slug)

        alice = self.make_participant('alice', claimed_time='now')
        self.take_last_week(team, alice, '40.00')
        team.set_take_for(alice, D('42.00'), team.owner)
        members = team.get_members(alice)
        assert len(members) == 2
        assert members[0]['username'] == 'alice'
        assert members[0]['take'] == 42
        assert members[0]['balance'] == 58
        assert members[1]['username'] == team.slug
        assert members[1]['take'] == 58


    # TODO - review this.
    #        should the final balance be 14 or zero?
    #        where do we use the final balance other than the UI?
    def test_compute_actual_takes_gives_correct_final_balance(self):
        team = self.make_team()

        # TODO - Change this to create a subscription after update_receiving is fixed.
        self.db.run("UPDATE teams SET receiving='100' WHERE slug=%s", (team.slug,))
        team = Team.from_slug(team.slug)

        alice = self.make_participant('alice', claimed_time='now')
        self.take_last_week(team, alice, '100.00')
        team.set_take_for(alice, D('86.00'), team.owner)
        takes = team.compute_actual_takes().values()
        assert len(takes) == 2
        assert takes[1]['balance'] == D('14')

    def test_taking_and_receiving_are_updated_correctly(self):
        team = self.make_team(is_approved=True)
        bob = self.make_participant('bob', claimed_time='now', last_bill_result='')
        bob.set_subscription_to(team, D('50.00'))

        alice = self.make_participant('alice', claimed_time='now')
        self.take_last_week(team, alice, '40.00')
        team.set_take_for(alice, D('42.00'), alice)
        assert alice.taking == alice.receiving == 42

        team.set_take_for(alice, D('50.00'), alice)
        assert alice.taking == alice.receiving == 50

        team.set_take_for(alice, D('60.00'), alice)
        assert alice.taking == alice.receiving == 50

    def test_changes_to_team_receiving_affect_members_take(self):
        team = self.make_team(is_approved=True)
        bob = self.make_participant('bob', claimed_time='now', last_bill_result='')
        bob.set_subscription_to(team, D('50.00'))

        alice = self.make_participant('alice', claimed_time='now')
        self.take_last_week(team, alice, '40.00')
        team.set_take_for(alice, D('42.00'), alice)

        bob.set_subscription_to(team, D('10.00'))  # hard times
        alice = Participant.from_username('alice')
        assert alice.receiving == alice.taking == 10

    def test_changes_to_others_take_affects_members_take(self):
        team = self.make_team(is_approved=True)
        bob = self.make_participant('bob', claimed_time='now', last_bill_result='')
        bob.set_subscription_to(team, D('100.00'))

        alice = self.make_participant('alice', claimed_time='now')
        self.take_last_week(team, alice, '30.00')
        team.set_take_for(alice, D('42.00'), alice)

        carl = self.make_participant('carl', claimed_time='now')
        self.take_last_week(team, carl, '50.00')
        team.set_take_for(carl, D('60.00'), carl)

        alice = Participant.from_username('alice')
        assert alice.receiving == alice.taking == 40

        # But get_members still uses nominal amount
        assert [m['take'] for m in  team.get_members(alice)] == [60, 42, 0]

    def test_changes_to_others_take_can_increase_members_take(self):
        team = self.make_team(is_approved=True)
        bob = self.make_participant('bob', claimed_time='now', last_bill_result='')
        bob.set_subscription_to(team, D('100.00'))

        alice = self.make_participant('alice', claimed_time='now')
        self.take_last_week(team, alice, '30.00')
        team.set_take_for(alice, D('42.00'), alice)

        carl = self.make_participant('carl', claimed_time='now')
        self.take_last_week(team, carl, '60.00')
        team.set_take_for(carl, D('80.00'), carl)
        alice = Participant.from_username('alice')
        assert alice.receiving == alice.taking == 20

        team.set_take_for(carl, D('30.00'), carl)
        alice = Participant.from_username('alice')
        assert alice.receiving == alice.taking == 42

    # get_take_last_week_for - gtlwf

    def test_gtlwf_works_during_payday(self):
        team = self.make_team()
        alice = self.make_participant('alice', claimed_time='now')
        self.take_last_week(team, alice, '30.00')
        take_this_week = D('42.00')
        team.set_take_for(alice, take_this_week, alice)
        self.db.run("INSERT INTO paydays DEFAULT VALUES")
        assert team.get_take_last_week_for(alice) == 30
        self.db.run("""
            INSERT INTO payments (team, participant, amount, direction)
                 VALUES (%s, %s, %s, 'to-participant')
        """, (team.slug, alice.username, take_this_week))
        assert team.get_take_last_week_for(alice) == 30

