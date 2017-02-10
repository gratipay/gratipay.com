# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing.harness import Harness


class TestACMEChallenge(Harness):

    def test_cant_find_the_real_dot_well_known(self):
        assert self.client.GxT('/.well-known/README').code == 404

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
