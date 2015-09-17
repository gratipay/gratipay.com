from __future__ import absolute_import, division, print_function, unicode_literals

from aspen import json, Response
from gratipay.testing import Harness
from pytest import raises


class Tests(Harness):

    def setUp(self):
        self.make_participant('admin', is_admin=True)
        self.db.run("INSERT INTO accounts VALUES ('100', 'Cash')")

    def load(self, number):
        return json.loads(self.client.GET('/api/v2/accounts/'+number, auth_as='admin').body)


    def test_can_list_accounts(self):
        actual = json.loads(self.client.GET('/api/v2/accounts/', auth_as='admin').body)
        assert actual == {"accounts": [{"number": "100", "name": "Cash"}]}

    def test_can_get_one_account(self):
        assert self.load('100') == {"number": "100", "name": "Cash"}

    def test_401_for_anon(self):
        assert self.client.GxT('/api/v2/accounts/').code == 401
        assert self.client.GxT('/api/v2/accounts/100').code == 401

    def test_403_for_non_admin(self):
        self.make_participant('alice')
        assert self.client.GxT('/api/v2/accounts/', auth_as='alice').code == 403
        assert self.client.GxT('/api/v2/accounts/100', auth_as='alice').code == 403

    def test_can_change_name(self):
        self.client.hit( 'PUT'
                       , '/api/v2/accounts/100'
                       , data={'number': '100', 'name': 'Cash'}
                       , auth_as='admin'
                        )
        assert self.load('100') == {"number": "100", "name": "Cash"}

    def test_bad_name_is_400(self):
        response = self.client.hit( 'PUT'
                                  , '/api/v2/accounts/100'
                                  , data={'number': '100', 'name': 'Cash!'}
                                  , auth_as='admin'
                                  , raise_immediately=False
                                  , **{b'HTTP_ACCEPT': b'application/json'}
                                   )
        assert response.code == 400
        assert json.loads(response.body)['error_message_long'] == 'Invalid name.'
        assert self.load('100') == {"number": "100", "name": "Cash"}

    def test_can_save_new_account(self):
        assert raises(Response, self.load, '101').value.code == 404
        self.client.hit( 'PUT'
                       , '/api/v2/accounts/101'
                       , data={'number': '101', 'name': 'Accounts Receivable'}
                       , auth_as='admin'
                        )
        assert self.load('101') == {"number": "101", "name": "Accounts Receivable"}

    def test_inserting_a_duplicate_name_is_400(self):
        response = self.client.hit( 'PUT'
                                  , '/api/v2/accounts/101'
                                  , data={'number': '101', 'name': 'Cash'}
                                  , auth_as='admin'
                                  , raise_immediately=False
                                  , **{b'HTTP_ACCEPT': b'application/json'}
                                   )
        assert response.code == 400
        assert json.loads(response.body)['error_message_long'] == \
                'Failed to upsert (101, Cash). Probably a duplicate name?'
        assert self.load('100') == {"number": "100", "name": "Cash"}
        assert raises(Response, self.load, '101').value.code == 404

    def test_updating_a_duplicate_name_is_400(self):
        self.client.hit( 'PUT'
                       , '/api/v2/accounts/101'
                       , data={'number': '101', 'name': 'Accounts Receivable'}
                       , auth_as='admin'
                        )
        response = self.client.hit( 'PUT'
                                  , '/api/v2/accounts/101'
                                  , data={'number': '101', 'name': 'Cash'}
                                  , auth_as='admin'
                                  , raise_immediately=False
                                  , **{b'HTTP_ACCEPT': b'application/json'}
                                   )
        assert response.code == 400
        assert json.loads(response.body)['error_message_long'] == \
                'duplicate key value violates unique constraint "accounts_name_key"\n' \
                'DETAIL:  Key (name)=(Cash) already exists.\n'
        assert self.load('100') == {"number": "100", "name": "Cash"}
        assert self.load('101') == {"number": "101", "name": "Accounts Receivable"}
