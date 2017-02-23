from __future__ import absolute_import, division, print_function, unicode_literals

from test_team_takes import TeamTakesHarness, PENNY
from gratipay.models.team.membership import Membership


class Tests(TeamTakesHarness):

    def setUp(self):
        TeamTakesHarness.setUp(self)

    def assert_memberships(self, *expected):
        actual = self.enterprise.get_memberships()
        assert [m['username'] for m in actual] == list(expected)


    def test_team_object_subclasses_takes_mixin(self):
        assert isinstance(self.enterprise, Membership)


    # gm - get_memberships

    def test_gm_returns_an_empty_list_when_there_are_no_members(self):
        assert self.enterprise.get_memberships() == []

    def test_gm_returns_memberships_when_there_are_members(self):
        self.enterprise.add_member(self.crusher, self.picard)
        assert len(self.enterprise.get_memberships()) == 1

    def test_gm_returns_more_memberships_when_there_are_more_members(self):
        self.enterprise.add_member(self.crusher, self.picard)
        self.enterprise.add_member(self.bruiser, self.picard)
        assert len(self.enterprise.get_memberships()) == 2

    def test_gm_sets_removal_allowed_to_true_when_removal_allowed(self):
        self.enterprise.add_member(self.bruiser, self.picard)
        memberships = self.enterprise.get_memberships(self.picard)
        assert memberships[0]['removal_allowed']

    def test_gm_sets_removal_allowed_to_false_when_removal_not_allowed(self):
        self.enterprise.add_member(self.bruiser, self.picard)
        memberships = self.enterprise.get_memberships(self.bruiser)
        assert not memberships[0]['removal_allowed']

    def test_gm_sets_editing_allowed_to_true_when_editing_allowed(self):
        self.enterprise.add_member(self.bruiser, self.picard)
        memberships = self.enterprise.get_memberships(self.bruiser)
        assert memberships[0]['editing_allowed']

    def test_gm_sets_editing_allowed_to_false_when_editing_not_allowed(self):
        self.enterprise.add_member(self.bruiser, self.picard)
        memberships = self.enterprise.get_memberships(self.picard)
        assert not memberships[0]['editing_allowed']

    def test_gm_sets_last_week(self):
        self.enterprise.add_member(self.bruiser, self.picard)
        self.run_payday()
        memberships = self.enterprise.get_memberships(self.picard)
        assert memberships[0]['last_week'] == PENNY


    # am - add_member

    def test_am_adds_a_member(self):
        self.enterprise.add_member(self.crusher, self.picard)
        self.assert_memberships('crusher')

    def test_am_adds_another_member(self):
        self.enterprise.add_member(self.crusher, self.picard)
        self.enterprise.add_member(self.bruiser, self.picard)
        self.assert_memberships('crusher', 'bruiser')

    def test_am_affects_computed_values_as_expected(self):
        self.enterprise.add_member(self.crusher, self.picard)
        self.enterprise.add_member(self.bruiser, self.picard)
        assert self.enterprise.nmembers == 2


    # rm - remove_member

    def test_rm_removes_a_member(self):
        self.enterprise.add_member(self.crusher, self.picard)
        self.enterprise.add_member(self.bruiser, self.picard)
        self.enterprise.remove_member(self.crusher, self.crusher)
        self.assert_memberships('bruiser')

    def test_rm_removes_another_member(self):
        self.enterprise.add_member(self.crusher, self.picard)
        self.enterprise.add_member(self.bruiser, self.picard)
        self.enterprise.remove_member(self.crusher, self.crusher)
        self.enterprise.remove_member(self.bruiser, self.picard)
        self.assert_memberships()

    def test_rm_affects_computed_values_as_expected(self):
        self.enterprise.add_member(self.crusher, self.picard)
        self.enterprise.add_member(self.bruiser, self.picard)
        self.enterprise.remove_member(self.crusher, self.crusher)
        assert self.enterprise.nmembers == 1
