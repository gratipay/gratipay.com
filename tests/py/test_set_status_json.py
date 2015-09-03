from __future__ import print_function, unicode_literals

from gratipay.testing import Harness
from gratipay.models.team import Team


class TestSetStatus(Harness):
    def setUp(self):
        Harness.setUp(self)
        self.admin = self.make_participant('admin', is_admin=True)
        self.alice = self.make_participant('alice')
        self.gratiteam = self.make_team('gratiteam', owner='alice', is_approved=None)

    def hit(self, data, auth_as='admin', expected=200):
        r = self.client.POST('/gratiteam/set-status.json',
                             data=data, auth_as=auth_as,
                             raise_immediately=False)

        assert r.code == expected
        return r

    def test_admin_can_modify_is_approved(self):
        assert self.gratiteam.is_approved is None

        # Change to Approved
        self.hit({'status': 'approved'})
        team = Team.from_slug('gratiteam')
        assert team.is_approved is True

        # Change to Rejected
        self.hit({'status': 'rejected'})
        team = Team.from_slug('gratiteam')
        assert team.is_approved is False

        # Change back to Approved
        self.hit({'status': 'approved'})
        team = Team.from_slug('gratiteam')
        assert team.is_approved is True

        # Change to Under Review
        self.hit({'status': 'unreviewed'})
        team = Team.from_slug('gratiteam')
        assert team.is_approved is None

    def test_400_for_bad_input(self):
        self.hit({'status': 'bad_input'}, expected=400)

    def test_403_for_non_admin(self):
        self.hit({'status': 'approved'}, expected=403, auth_as='alice')

    def test_setting_adds_event(self):
        self.hit({'status': 'approved'})

        actual = self.db.one("SELECT type, payload FROM events")
        assert actual.type == 'team'
        assert actual.payload == {
            'id': self.gratiteam.id,
            'recorder': {'id': self.admin.id, 'username':self.admin.username},
            'action': 'set',
            'values': {'status': 'approved'}
        }
