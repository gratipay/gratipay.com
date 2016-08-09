from __future__ import unicode_literals

import json

from gratipay.testing import Harness

class TestLookupJson(Harness):

    def lookup(self, q):
        response = self.client.GET('/lookup.json?query={}'.format(q))
        data = json.loads(response.body)
        return [d['id'] for d in data]


    def make_alice(self, **kw):
        kw.update(claimed_time='now', email_address='alice@example.com', verified_in='TT')
        return self.make_participant("alice", **kw)

    def test_get_without_query_returns_400(self):
        response = self.client.GxT('/lookup.json')
        assert response.code == 400

    def test_looking_up_non_existent_user_finds_nothing(self):
        assert self.lookup('alice') == [-1]

    def test_looking_up_non_searchable_user_with_an_exact_match_finds_them(self):
        alice = self.make_alice(is_searchable=False)
        assert self.lookup('alice') == [alice.id]

    def test_looking_up_non_searchable_user_without_exact_match_finds_nothing(self):
        self.make_alice(is_searchable=False)
        assert self.lookup('alic') == [-1]

    def test_looking_up_searchable_user_with_an_exact_match_finds_them(self):
        alice = self.make_alice()
        assert self.lookup('alice') == [alice.id]

    def test_looking_up_searchable_user_without_an_exact_match_finds_them(self):
        alice = self.make_alice()
        assert self.lookup('alic') == [alice.id, -1]


    def test_looking_up_suspicious_user_finds_nothing(self):
        self.make_participant( "alice"
                             , claimed_time='now'
                             , verified_in='TT'
                             , email_address='alice@example.com'
                             , is_suspicious=True
                              )
        assert self.lookup('alice') == [-1]

    def test_looking_up_unverified_user_finds_nothing(self):
        self.make_participant("alice", claimed_time='now', email_address='alice@example.com')
        assert self.lookup('alice') == [-1]

    def test_looking_up_user_with_no_email_finds_nothing(self):
        self.make_participant("alice", claimed_time='now')  # can't verify w/o email!
        assert self.lookup('alice') == [-1]

    def test_looking_up_unclaimed_user_finds_nothing(self):
        self.make_participant("alice", verified_in='TT', email_address='alice@example.com')
        assert self.lookup('alice') == [-1]
