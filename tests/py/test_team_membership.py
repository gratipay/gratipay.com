from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing import Harness
from gratipay.models.team import Team, mixins
from pytest import raises


class Tests(Harness):

    def setUp(self):
        self.enterprise = self.make_team('The Enterprise')
        self.crusher = self.make_participant( 'crusher'
                                            , email_address='alice@example.com'
                                            , claimed_time='now'
                                             )
        TT = self.db.one("SELECT id FROM countries WHERE code2='TT'")
        self.crusher.store_identity_info(TT, 'nothing-enforced', {'name': 'Crusher'})
        self.crusher.set_identity_verification(TT, True)


    def test_team_object_subclasses_takes_mixin(self):
        assert isinstance(self.enterprise, mixins.Membership)

    def test_takes_enabled_defaults_to_false(self):
        assert self.enterprise.takes_enabled is False


    # ste - set_takes_enabled

    def test_ste_sets_takes_enabled(self):
        self.enterprise.set_takes_enabled(True)
        assert Team.from_slug('TheEnterprise').takes_enabled is True

    def test_ste_sets_takes_enabled_back_to_false(self):
        self.enterprise.set_takes_enabled(False)
        assert Team.from_slug('TheEnterprise').takes_enabled is False

    def test_ste_sets_takes_rejects_non_boolean_values(self):
        raises(TypeError, self.enterprise.set_takes_enabled, None)
        raises(TypeError, self.enterprise.set_takes_enabled, 'foo')
        raises(TypeError, self.enterprise.set_takes_enabled, 123)

    def test_ste_setting_takes_enabled_is_a_logged_event(self):
        self.enterprise.set_takes_enabled(True)
        events = self.db.all("SELECT * FROM events ORDER BY ts DESC")
        assert events[0].type == 'team'
        assert events[0].payload['action'] == 'set takes_enabled'
        assert events[0].payload['old_value'] == False
        assert events[0].payload['new_value'] == True
        assert events[0].payload['id'] == self.enterprise.id


    # gm - get_memberships

    def test_gm_returns_an_empty_list_when_there_are_no_members(self):
        assert self.enterprise.get_memberships() == []


    # um - update_memberhip

    def test_um_updates_membership(self):
        assert self.enterprise.update_membership(self.crusher, 537) == 537

    def test_um_actually_updates_membership(self):
        self.enterprise.update_membership(self.crusher, 537)
        memberships = self.enterprise.get_memberships()
        assert [(m.participant.username, m.ntakes) for m in memberships] == [('crusher', 537)]
