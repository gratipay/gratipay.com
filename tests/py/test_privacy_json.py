from __future__ import print_function, unicode_literals

from aspen import json
from gratipay.testing import Harness


class Tests(Harness):
    def setUp(self):
        Harness.setUp(self)
        self.make_participant('alice', claimed_time='now')

    def hit_privacy(self, method='GET', expected_code=200, **kw):
        response = self.client.hit(method, "/~alice/privacy.json", auth_as='alice', **kw)
        if response.code != expected_code:
            print(response.body)
        return response

    def test_participant_can_get_their_privacy_settings(self):
        response = self.hit_privacy('GET')
        actual = json.loads(response.body)
        assert actual == {
            'is_searchable': True,
            'anonymous_giving': False,
        }

    def test_participant_can_toggle_is_searchable(self):
        response = self.hit_privacy('POST', data={'toggle': 'is_searchable'})
        actual = json.loads(response.body)
        assert actual['is_searchable'] is False

    def test_participant_can_toggle_is_searchable_back(self):
        response = self.hit_privacy('POST', data={'toggle': 'is_searchable'})
        response = self.hit_privacy('POST', data={'toggle': 'is_searchable'})
        actual = json.loads(response.body)
        assert actual['is_searchable'] is True

    def test_participant_can_toggle_anonymous_giving(self):
        response = self.hit_privacy('POST', data={'toggle': 'anonymous_giving'})
        actual = json.loads(response.body)
        assert actual['anonymous_giving'] is True

    def test_participant_can_toggle_anonymous_giving_back(self):
        response = self.hit_privacy('POST', data={'toggle': 'anonymous_giving'})
        response = self.hit_privacy('POST', data={'toggle': 'anonymous_giving'})
        actual = json.loads(response.body)['anonymous_giving']
        assert actual is False

    # Related to is-searchable

    def test_meta_robots_tag_added_on_opt_out(self):
        self.hit_privacy('POST', data={'toggle': 'is_searchable'})
        expected = '<meta name="robots" content="noindex,nofollow" />'
        assert expected in self.client.GET("/~alice/").body

    def test_participant_does_show_up_on_search(self):
        assert 'alice' in self.client.GET("/search?q=alice").body

    def test_participant_doesnt_show_up_on_search(self):
        self.hit_privacy('POST', data={'toggle': 'is_searchable'})
        assert 'alice' not in self.client.GET("/search.json?q=alice").body

    # Related to anonymous_giving

    def test_anon_can_see_giving_for_non_anonymous_giving(self):
        self.make_participant('bob', claimed_time='now',
                              giving=10.79, ngiving_to=342, anonymous_giving=False)
        assert '10.79' in self.client.GET('/~bob/').body
        assert '342' in self.client.GET('/~bob/').body

    def test_auth_can_see_giving_for_non_anonymous_giving(self):
        self.make_participant('bob', claimed_time='now',
                              giving=10.79, ngiving_to=342, anonymous_giving=False)
        assert '10.79' in self.client.GET('/~bob/', auth_as='alice').body
        assert '342' in self.client.GET('/~bob/', auth_as='alice').body

    def test_admin_can_see_giving_for_non_anonymous_giving(self):
        self.make_participant('bob', claimed_time='now',
                              giving=10.79, ngiving_to=342, anonymous_giving=False)
        self.make_participant('admin', is_admin=True)
        assert '10.79' in self.client.GET('/~bob/', auth_as='admin').body
        assert '342' in self.client.GET('/~bob/', auth_as='admin').body
        assert '[342]' not in self.client.GET('/~bob/', auth_as='admin').body

    def test_self_can_see_giving_for_non_anonymous_giving(self):
        self.make_participant('bob', claimed_time='now',
                              giving=10.79, ngiving_to=342, anonymous_giving=False)
        assert '10.79' in self.client.GET('/~bob/', auth_as='bob').body.decode('utf8')
        assert '342' in self.client.GET('/~bob/', auth_as='bob').body.decode('utf8')
        assert '[342]' not in self.client.GET('/~bob/', auth_as='bob').body.decode('utf8')

    def test_anon_cannot_see_giving_for_anonymous_giving(self):
        self.make_participant('bob', claimed_time='now',
                              giving=10.79, ngiving_to=342, anonymous_giving=True)
        assert '10.79' not in self.client.GET('/~bob/').body
        assert '342' not in self.client.GET('/~bob/').body

    def test_auth_cannot_see_giving_for_anonymous_giving(self):
        self.make_participant('bob', claimed_time='now',
                              giving=10.79, ngiving_to=342, anonymous_giving=True)
        assert '10.79' not in self.client.GET('/~bob/', auth_as='alice').body
        assert '342' not in self.client.GET('/~bob/', auth_as='alice').body

    def test_admin_can_see_giving_for_anonymous_giving(self):
        self.make_participant('bob', claimed_time='now',
                              giving=10.79, ngiving_to=342, anonymous_giving=True)
        self.make_participant('admin', is_admin=True)
        assert '10.79' in self.client.GET('/~bob/', auth_as='admin').body
        assert '[342]' in self.client.GET('/~bob/', auth_as='admin').body

    def test_self_can_see_giving_for_anonymous_giving(self):
        self.make_participant('bob', claimed_time='now',
                              giving=10.79, ngiving_to=342, anonymous_giving=True)
        assert '10.79' in self.client.GET('/~bob/', auth_as='bob').body.decode('utf8')
        assert '[342]' in self.client.GET('/~bob/', auth_as='bob').body.decode('utf8')
