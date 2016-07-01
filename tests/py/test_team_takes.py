from __future__ import absolute_import, division, print_function, unicode_literals

from pytest import raises
from gratipay.models.participant import Participant
from gratipay.models.team import Team
from gratipay.models.team.mixins.takes import NotAllowed, PENNY, ZERO
from gratipay.testing import Harness


T = Team.from_slug
P = Participant.from_username


class TeamTakesHarness(Harness):
    # Factored out to share with membership tests ...

    def setUp(self):
        self.enterprise = self.make_team('The Enterprise')
        self.picard = P('picard')

        self.TT = self.db.one("SELECT id FROM countries WHERE code='TT'")

        self.crusher = self.make_participant( 'crusher'
                                            , email_address='crusher@example.com'
                                            , claimed_time='now'
                                             )
        self.crusher.store_identity_info(self.TT, 'nothing-enforced', {'name': 'Crusher'})
        self.crusher.set_identity_verification(self.TT, True)

        self.bruiser = self.make_participant( 'bruiser'
                                            , email_address='bruiser@example.com'
                                            , claimed_time='now'
                                             )
        self.bruiser.store_identity_info(self.TT, 'nothing-enforced', {'name': 'Bruiser'})
        self.bruiser.set_identity_verification(self.TT, True)


class Tests(TeamTakesHarness):

    # gtf - get_take_for

    def test_gtf_returns_zero_for_unknown(self):
        assert self.enterprise.get_take_for(self.crusher) == 0

    def test_gtf_returns_amount_for_known(self):
        self.enterprise.set_take_for(self.crusher, PENNY, self.picard)
        assert self.enterprise.get_take_for(self.crusher) == PENNY

    def test_gtf_returns_correct_amount_for_multiple_members(self):
        self.enterprise.set_take_for(self.crusher, PENNY, self.picard)
        self.enterprise.set_take_for(self.bruiser, PENNY, self.picard)
        self.enterprise.set_take_for(self.bruiser, PENNY * 2, self.bruiser)
        assert self.enterprise.get_take_for(self.crusher) == PENNY
        assert self.enterprise.get_take_for(self.bruiser) == PENNY * 2

    def test_gtf_returns_correct_amount_for_multiple_teams(self):
        self.enterprise.set_take_for(self.crusher, PENNY, self.picard)

        trident = self.make_team('The Trident', owner='shelby')
        trident.set_take_for(self.crusher, PENNY, P('shelby'))
        trident.set_take_for(self.crusher, PENNY * 2, self.crusher)

        assert self.enterprise.get_take_for(self.crusher) == PENNY
        assert trident.get_take_for(self.crusher) == PENNY * 2


    # stf - set_take_for

    def test_stf_sets_take_for_new_member(self):
        self.enterprise.set_take_for(self.crusher, PENNY, self.picard)
        assert self.enterprise.get_take_for(self.crusher) == PENNY

    def test_stf_updates_take_for_an_existing_member(self):
        self.enterprise.set_take_for(self.crusher, PENNY, self.picard)
        self.enterprise.set_take_for(self.crusher, 537, self.crusher)
        assert self.enterprise.get_take_for(self.crusher) == 537


    def test_stf_can_increase_ndistributing_to(self):
        self.enterprise.set_take_for(self.bruiser, PENNY, self.picard)
        assert self.enterprise.ndistributing_to == 1
        self.enterprise.set_take_for(self.crusher, PENNY, self.picard)
        assert self.enterprise.ndistributing_to == 2

    def test_stf_doesnt_increase_ndistributing_to_for_an_existing_member(self):
        self.enterprise.set_take_for(self.crusher, PENNY, self.picard)
        self.enterprise.set_take_for(self.crusher, PENNY, self.crusher)
        self.enterprise.set_take_for(self.crusher, 64, self.crusher)
        assert self.enterprise.ndistributing_to == 1

    def test_stf_can_decrease_ndistributing_to(self):
        self.enterprise.set_take_for(self.bruiser, PENNY, self.picard)
        self.enterprise.set_take_for(self.crusher, PENNY, self.picard)
        self.enterprise.set_take_for(self.crusher, 0, self.crusher)
        assert self.enterprise.ndistributing_to == 1
        self.enterprise.set_take_for(self.bruiser, 0, self.bruiser)
        assert self.enterprise.ndistributing_to == 0

    def test_stf_doesnt_decrease_ndistributing_to_below_zero(self):
        self.enterprise.set_take_for(self.crusher, PENNY, self.picard)
        self.enterprise.set_take_for(self.crusher, 0, self.picard)
        self.enterprise.set_take_for(self.crusher, 0, self.picard)
        self.enterprise.set_take_for(self.crusher, 0, self.picard)
        self.enterprise.set_take_for(self.crusher, 0, self.picard)
        assert self.enterprise.ndistributing_to == 0

    def test_stf_updates_ndistributing_to_in_the_db(self):
        self.enterprise.set_take_for(self.crusher, PENNY, self.picard)
        assert T('TheEnterprise').ndistributing_to == 1


    def test_stf_updates_taking_for_member(self):
        assert self.crusher.taking == ZERO
        self.enterprise.set_take_for(self.crusher, PENNY, self.picard)
        assert self.crusher.taking == PENNY


    # stf permissions

    def test_stf_lets_owner_add_member(self):
        self.enterprise.set_take_for(self.crusher, PENNY, self.picard)
        assert self.enterprise.ndistributing_to == 1

    def test_stf_lets_owner_add_themselves(self):
        self.enterprise.set_take_for(self.picard, PENNY, self.picard)
        assert self.enterprise.ndistributing_to == 1

    def test_stf_lets_owner_remove_member(self):
        self.enterprise.set_take_for(self.crusher, PENNY, self.picard)
        self.enterprise.set_take_for(self.crusher, ZERO, self.picard)
        assert self.enterprise.ndistributing_to == 0

    def test_stf_lets_owner_remove_themselves(self):
        self.enterprise.set_take_for(self.picard, PENNY, self.picard)
        self.enterprise.set_take_for(self.picard, ZERO, self.picard)
        assert self.enterprise.ndistributing_to == 0

    def err(self, *a):
        return raises(NotAllowed, self.enterprise.set_take_for, *a).value.args[0]

    def test_stf_doesnt_let_owner_increase_take_beyond_a_penny(self):
        actual = self.err(self.crusher, PENNY * 2, self.picard)
        assert actual == 'owner can only add and remove members, not otherwise set takes'

    def test_stf_doesnt_let_anyone_else_set_a_take(self):
        actual = self.err(self.crusher, PENNY * 1, self.bruiser)
        assert actual == 'can only set own take'

    def test_stf_doesnt_let_anyone_else_set_a_take_even_to_zero(self):
        actual = self.err(self.crusher, 0, self.bruiser)
        assert actual == 'can only set own take'

    def test_stf_doesnt_let_anyone_set_a_take_who_is_not_already_on_the_team(self):
        actual = self.err(self.crusher, PENNY, self.crusher)
        assert actual == 'can only set take if already a member of the team'

    def test_stf_doesnt_let_anyone_set_a_take_who_is_not_already_on_the_team_even_to_zero(self):
        actual = self.err(self.crusher, 0, self.crusher)
        assert actual == 'can only set take if already a member of the team'
