# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing.harness import Harness


class TestACMEChallenge(Harness):

    def test_cant_find_the_real_dot_well_known(self):
        assert self.client.GxT('/.well-known/README').code == 404

    def test_index_requires_admin(self):
        self.make_participant('alice')
        assert self.client.GxT('/.well-known/acme-challenge/').code == 401
        assert self.client.GxT('/.well-known/acme-challenge/', auth_as='alice').code == 403

    def test_index_shows_number(self):
        self.db.run("insert into acme_challenges values ('a', 'b')")
        self.db.run("insert into acme_challenges values ('a', 'b')")
        self.db.run("insert into acme_challenges values ('a', 'b')")
        self.make_participant('alice', is_admin=True)
        body = self.client.GET('/.well-known/acme-challenge/', auth_as='alice').body
        assert '<b>3</b>' in body

    def test_anon_sees_401_when_empty(self):
        assert self.client.GxT('/.well-known/acme-challenge/deadbeef').code == 401

    def test_auth_sees_403_when_empty(self):
        self.make_participant('alice', claimed_time='now')
        assert self.client.GxT('/.well-known/acme-challenge/deadbeef', auth_as='alice').code == 403

    def test_anon_sees_404_for_wrong_token(self):
        self.db.run("insert into acme_challenges values ('deadbeef', 'beefdeaf')")
        response = self.client.GxT('/.well-known/acme-challenge/feeeeeee')
        response.code == 404

    def test_anon_receives_authorization_response_for_right_token(self):
        self.db.run("insert into acme_challenges values ('deadbeef', 'beefdeaf')")
        response = self.client.GxT('/.well-known/acme-challenge/deadbeef')
        response.code, response.body == 200, 'deadbeef'

    def test_so_does_auth_for_that_matter(self):
        self.make_participant('alice', claimed_time='now')
        self.db.run("insert into acme_challenges values ('deadbeef', 'beefdeaf')")
        response = self.client.GxT('/.well-known/acme-challenge/deadbeef', auth_as='alice')
        response.code, response.body == 200, 'deadbeef'

    def test_admin_sees_form(self):
        self.make_participant('alice', claimed_time='now', is_admin=True)
        self.db.run("insert into acme_challenges values ('deadbeef', 'beefdeaf')")
        actual = self.client.GET('/.well-known/acme-challenge/deadbeef', auth_as='alice').body
        assert '<form action="/.well-known/acme-challenge/deadbeef"' in actual

    def test_anon_cant_post_form(self):
        assert self.client.PxST('/.well-known/acme-challenge/foo').code == 405

    def test_auth_cant_post_form(self):
        self.make_participant('alice', claimed_time='now')
        assert self.client.PxST('/.well-known/acme-challenge/foo', auth_as='alice').code == 405

    def test_admin_can_post_form(self):
        self.make_participant('alice', claimed_time='now', is_admin=True)
        actual = self.client.POST( '/.well-known/acme-challenge/deadbeef'
                                 , auth_as='alice'
                                 , data={'authorization': 'rawr'}
                                  ).body
        assert '<pre>rawr</pre>' in actual

    def test_posting_overwrites_existing(self):
        self.make_participant('alice', claimed_time='now', is_admin=True)
        self.client.POST( '/.well-known/acme-challenge/deadbeef'
                        , auth_as='alice'
                        , data={'authorization': 'rawr'}
                         )
        self.client.POST( '/.well-known/acme-challenge/deadbeef'
                        , auth_as='alice'
                        , data={'authorization': 'roo'}
                         )
        assert self.db.one('SELECT "authorization" FROM acme_challenges') == 'roo'

    def test_getting_destroys_evidence(self):
        self.make_participant('alice', claimed_time='now', is_admin=True)
        self.client.POST( '/.well-known/acme-challenge/deadbeef'
                        , auth_as='alice'
                        , data={'authorization': 'rawr'}
                         )
        self.client.GxT('/.well-known/acme-challenge/deadbeef')
        assert self.db.one('SELECT "authorization" FROM acme_challenges') is None


class TestAssetsACMEChallenge(Harness):

    def test_cant_find_the_real_dot_well_known(self):
        assert self.client.GxT('/assets/.well-known/README').code == 404

    def test_the_index_is_empty(self):
        assert self.client.GxT('/assets/.well-known/acme-challenge/').code == 404

    def test_missing_is_404(self):
        self.db.run("insert into acme_challenges values ('deadbeef', 'beefdeaf')")
        assert self.client.GxT('/assets/.well-known/acme-challenge/fooooooo').code == 404

    def test_authorization_is_available(self):
        self.db.run("insert into acme_challenges values ('deadbeef', 'beefdeaf')")
        assert self.client.GxT('/assets/.well-known/acme-challenge/deadbeef').body == 'beefdeaf'

    def test_getting_destroys_evidence(self):
        self.db.run("insert into acme_challenges values ('deadbeef', 'beefdeaf')")
        self.client.GxT('/assets/.well-known/acme-challenge/deadbeef')
        assert self.db.one('SELECT "authorization" FROM acme_challenges') is None

    def test_admins_can_set_from_non_assets(self):
        self.make_participant('alice', claimed_time='now', is_admin=True)
        self.client.POST( '/.well-known/acme-challenge/deadbeef'
                        , auth_as='alice'
                        , data={'authorization': 'rawr'}
                         )
        assert self.client.GxT('/assets/.well-known/acme-challenge/deadbeef').body == 'rawr'

    def test_results_are_not_cached(self):
        self.db.run("insert into acme_challenges values ('deadbeef', 'beefdeaf')")
        response = self.client.GET( '/assets/.well-known/acme-challenge/foo'
                                  , raise_immediately=False
                                   )
        assert response.headers['Cache-Control'] == 'no-cache'
