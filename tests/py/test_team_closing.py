# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing import Harness


class TestTeamClosing(Harness):

    def test_teams_can_be_closed(self):
        team = self.make_team()
        team.close()
        assert team.is_closed
