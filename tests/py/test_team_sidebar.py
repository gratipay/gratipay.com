from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing import Harness

class TeamSidebarHarness(Harness):

        def setUp(self):
            self.admin = self.make_participant('admin', is_admin=True)
            self.picard = self.make_participant('picard')
            self.bob   = self.make_participant('bob')
            self.make_team(name='approved', is_approved=True, available=100)

class Tests(TeamSidebarHarness):

    def test_sidebar_set_status_visible_to_admin_only(self):
        for user in ['picard', 'bob', 'admin']:
            data = self.client.GET('/approved/', auth_as=user)
            assert data.code == 200
            if user == 'admin':
                assert 'Set Status' in data.body
            else:
                assert 'Set Status' not in data.body

    def test_sidebar_nav_visible_to_admin_and_owner_only(self):
        for user in ['picard', 'bob', 'admin']:
            data = self.client.GET('/approved/', auth_as=user)
            assert data.code == 200
            if user == 'bob':
                assert 'Profile' not in data.body
            else:
                assert 'Profile' in data.body

    def test_sidebar_nav_visible_to_approved_teams_only(self):
        self.make_team(name='not-approved')

        data = self.client.GET('/approved/', auth_as='picard')
        assert 'Profile' in data.body
        data = self.client.GET('/not-approved/', auth_as='picard')
        assert 'Profile' not in data.body

    def test_sidebar_distributing_visible_to_owner_only(self):
        data = self.client.GET('/approved/', auth_as='picard')
        assert 'Distributing' in data.body
        data = self.client.GET('/approved/', auth_as='bob')
        assert 'Distributing' not in data.body

    def test_sidebar_distributing_visible_when_available_only(self):
        self.make_team(name='approved-nothing-available', is_approved=True, owner='picard')

        data = self.client.GET('/approved/', auth_as='picard')
        assert 'Distributing' in data.body
        data = self.client.GET('/approved-nothing-available/', auth_as='picard')
        assert 'Distributing' not in data.body
