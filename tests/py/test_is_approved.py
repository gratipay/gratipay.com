from __future__ import print_function, unicode_literals

from gratipay.testing import Harness
from gratipay.models.team import Team


class TestIsApproved(Harness):
    def setUp(self):
        Harness.setUp(self)
        self.admin = self.make_participant('admin', is_admin=True)
        self.alice = self.make_participant('alice')
        self.gratiteam = self.make_team('gratiteam', owner='alice')

    def hit(self, data, auth_as='admin', expected=200):
        r = self.client.POST('/gratiteam/toggle-is-approved.json',
                             data=data, auth_as=auth_as,
                             raise_immediately=False)

        assert r.code == expected
        return r

    def test_admin_can_modify_is_approved(self):
        assert self.gratiteam.is_approved == None

        # Change to True
        self.hit({'to': 'true'})
        team = Team.from_slug('gratiteam')
        assert team.is_approved == True

        # Change to False
        self.hit({'to': 'false'})
        team = Team.from_slug('gratiteam')
        assert team.is_approved == False

    def test_400_for_bad_input(self):
        self.hit({'to': 'bad_input'}, expected=400)

    def test_403_for_non_admin(self):
        self.hit({'to': 'true'}, expected=403, auth_as='alice')

    def test_toggling_adds_event(self):
        self.hit({'to': 'true'})

        actual = self.db.one("SELECT type, payload FROM events")
        assert actual.type == 'team'
        assert actual.payload == {
            'id': self.gratiteam.id,
            'recorder': {'id': self.admin.id, 'username':self.admin.username},
            'action': 'set',
            'values': {'is_approved': True}
        }
