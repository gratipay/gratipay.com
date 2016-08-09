from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing import Harness


class Tests(Harness):

    def setUp(self):
        self.admin = self.make_participant('admin', is_admin=True)
        self.picard = self.make_participant('picard')
        self.bob = self.make_participant('bob')
        self.make_team(name='approved', is_approved=True, available=100)


    def test_set_status_visible_to_admin(self):
        assert 'Set Status' in self.client.GET('/approved/', auth_as='admin').body

    def test_set_status_not_visible_to_owner(self):
        assert 'Set Status' not in self.client.GET('/approved/', auth_as='picard').body

    def test_set_status_not_visible_to_rando(self):
        assert 'Set Status' not in self.client.GET('/approved/', auth_as='bob').body


    def test_nav_visible_to_admin(self):
        assert 'Profile' in self.client.GET('/approved/', auth_as='admin').body

    def test_nav_visible_to_owner(self):
        assert 'Profile' in self.client.GET('/approved/', auth_as='picard').body

    def test_nav_not_visible_to_rando(self):
        assert 'Profile' not in self.client.GET('/approved/', auth_as='bob').body

    def test_nav_not_visible_to_unapproved_team_owner(self):
        self.make_team(name='not-approved', is_approved=False, owner='picard')
        assert 'Profile' not in self.client.GET('/not-approved/', auth_as='picard').body


    def test_distributing_visible_to_owner(self):
        assert 'Distributing' in self.client.GET('/approved/', auth_as='picard').body

    def test_distributing_not_visible_to_rando(self):
        assert 'Distributing' not in self.client.GET('/approved/', auth_as='bob').body

    def test_distributing_not_visible_to_owner_without_available(self):
        self.make_team(name='approved-nothing-available', is_approved=True, owner='picard')
        data = self.client.GET('/approved-nothing-available/', auth_as='picard')
        assert 'Distributing' not in data.body
