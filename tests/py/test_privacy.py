from __future__ import print_function, unicode_literals

from gratipay.testing import Harness
from psycopg2 import IntegrityError


class Tests(Harness):

    def setUp(self):
        Harness.setUp(self)
        self.make_participant('alice', claimed_time='now')

    def hit_privacy(self, expected_code=200, **kw):
        response = self.client.POST("/alice/account/privacy", auth_as='alice', **kw)
        if response.code != expected_code:
            print(response.body)
        return response


    fields = ( "is_searchable"
             , "public_giving"
             , "public_receiving"
             , "public_supporting"
             , "public_supporters"
             , "tell_supporting"
             , "know_supporters"
              )

    def test_can_set_privacy_preference_to_false(self):
        for field in self.fields:
            response = self.hit_privacy(data={'field': field, 'value': 'false'})
            assert response.body == 'false'

    def test_can_set_privacy_preference_to_true(self):
        for field in self.fields:
            response = self.hit_privacy(data={'field': field, 'value': 'true'})
            assert response.body == 'true'

    def test_can_set_know_supporters_to_null(self):
        for field in self.fields:
            try:
                response = self.hit_privacy(data={'field': field, 'value': 'null'})
            except Exception as exc:
                pass
            if field == 'know_supporters':
                assert response.body == 'null'
            else:
                assert exc.__class__ is IntegrityError


    # is_searchable

    def test_meta_robots_tag_added_on_opt_out(self):
        self.hit_privacy('POST', data={'field': 'is_searchable', 'value': 'false'})
        expected = '<meta name="robots" content="noindex,nofollow" />'
        assert expected in self.client.GET("/alice/").body

    def test_participant_does_show_up_on_search(self):
        assert 'alice' in self.client.GET("/search?q=alice").body

    def test_participant_doesnt_show_up_on_search(self):
        self.hit_privacy('POST', data={'field': 'is_searchable', 'value': 'false'})
        assert 'alice' not in self.client.GET("/search?q=alice").body
