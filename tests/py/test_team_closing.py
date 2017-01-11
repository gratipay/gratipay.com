# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing import Harness, T


class TestTeamClosing(Harness):

    def test_teams_can_be_closed_via_python(self):
        team = self.make_team()
        team.close()
        assert team.is_closed

    def test_teams_can_be_closed_via_http(self):
        self.make_team()
        response = self.client.PxST('/TheEnterprise/edit/close', auth_as='picard')
        assert response.headers['Location'] == '/~picard/'
        assert response.code == 302
        assert T('TheEnterprise').is_closed

    def test_but_not_by_anon(self):
        self.make_team()
        response = self.client.PxST('/TheEnterprise/edit/close')
        assert response.code == 401

    def test_nor_by_turkey(self):
        self.make_participant('turkey')
        self.make_team()
        response = self.client.PxST('/TheEnterprise/edit/close', auth_as='turkey')
        assert response.code == 403

    def test_admin_is_cool_though(self):
        self.make_participant('Q', is_admin=True)
        self.make_team()
        response = self.client.PxST('/TheEnterprise/edit/close', auth_as='Q')
        assert response.headers['Location'] == '/~Q/'
        assert response.code == 302
        assert T('TheEnterprise').is_closed
