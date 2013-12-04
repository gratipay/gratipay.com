from __future__ import print_function, unicode_literals

from aspen import json

from gittip.elsewhere.twitter import TwitterAccount
from gittip.testing import Harness
from gittip.testing.client import TestClient


class Tests(Harness):

    def hit_anonymous(self, method='GET', data={}, expected_code=200):
        user, ignored = TwitterAccount(self.db, 'alice', {}).opt_in('alice')

        client = TestClient()
        response = client.get('/')
        csrf_token = response.request.context['csrf_token']

        if method == 'GET':
            response = client.get( "/alice/anonymous.json"
                                 , user='alice'
                                  )
        else:
            assert method == 'POST'
            response = client.post( "/alice/anonymous.json"
                                  , dict(data, csrf_token=csrf_token)
                                  , user='alice'
                                   )
        if response.code != expected_code:
            print(response.body)
        return response


    def test_participant_can_get_their_anonymity_settings(self):
        response = self.hit_anonymous('GET')
        actual = json.loads(response.body)
        assert actual == {'giving': False, 'receiving': False}

    def test_participant_can_toggle_anonymous_giving(self):
        response = self.hit_anonymous('POST', data={'toggle': 'giving'})
        actual = json.loads(response.body)
        assert actual['giving'] is True

    def test_participant_can_toggle_anonymous_receiving(self):
        response = self.hit_anonymous('POST', data={'toggle': 'receiving'})
        actual = json.loads(response.body)
        assert actual['receiving'] is True

    def test_participant_can_toggle_anonymous_giving_back(self):
        response = self.hit_anonymous('POST', data={'toggle': 'giving'})
        response = self.hit_anonymous('POST', data={'toggle': 'giving'})
        actual = json.loads(response.body)['giving']
        assert actual is False

    def test_participant_can_toggle_anonymous_receiving_back(self):
        response = self.hit_anonymous('POST', data={'toggle': 'receiving'})
        response = self.hit_anonymous('POST', data={'toggle': 'receiving'})
        actual = json.loads(response.body)['receiving']
        assert actual is False
