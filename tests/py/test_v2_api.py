from __future__ import absolute_import, division, print_function, unicode_literals

from aspen import json
from gratipay.testing import Harness


class Tests(Harness):

    def load(self, auth_as=None):
        response = self.client.GET( '/api/v2/'
                                  , auth_as=auth_as
                                  , **{b'HTTP_ACCEPT': b'application/json'
                                   })
        return json.loads(response.body)

    def test_anon_gets_anon(self):
        assert self.load() == {'you': 'anon'}

    def test_non_anon_gets_their_username(self):
        self.make_participant('alice')
        assert self.load('alice') == {'you': 'alice'}
