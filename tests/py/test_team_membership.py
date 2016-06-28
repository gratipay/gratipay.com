from __future__ import absolute_import, division, print_function, unicode_literals

from test_team_takes import TeamTakesHarness
from gratipay.models.team import mixins


class Tests(TeamTakesHarness):

    def setUp(self):
        TeamTakesHarness.setUp(self)

    def assert_memberships(self, *expected):
        actual = self.enterprise.get_memberships()
        assert [m['username'] for m in actual] == list(expected)


    def test_team_object_subclasses_takes_mixin(self):
        assert isinstance(self.enterprise, mixins.Membership)


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
