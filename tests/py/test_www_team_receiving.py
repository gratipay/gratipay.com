from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing import Harness


class Tests(Harness):

    def test_receiving_returns_404_for_unapproved_teams(self):
        self.make_team(is_approved=False)

        assert self.client.GxT('/TheEnterprise/receiving/').code == 404

    def test_receiving_is_not_visible_to_anon(self):
        self.make_team(is_approved=True)

        assert self.client.GxT('/TheEnterprise/receiving/', auth_as=None).code == 401

    def test_receiving_is_not_visible_to_random(self):
        self.make_team(is_approved=True)
        self.make_participant('alice')

        assert self.client.GxT('/TheEnterprise/receiving/', auth_as='alice').code == 403

    def test_receiving_is_visible_to_admin(self):
        self.make_team(is_approved=True)
        self.make_participant('admin', is_admin=True)

        assert self.client.GET('/TheEnterprise/receiving/', auth_as='admin').code == 200

    def test_receiving_is_visible_to_team_owner(self):
        self.make_team(is_approved=True)

        assert self.client.GET('/TheEnterprise/receiving/', auth_as='picard').code == 200