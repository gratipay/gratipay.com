# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.security import csrf
from gratipay.testing import Harness


class Tests(Harness):

    # st - _sanitize_token

    def test_st_passes_through_good_token(self):
        token = 'ddddeeeeaaaaddddbbbbeeeeeeeeffff'
        assert csrf._sanitize_token(token) == token

    def test_st_rejects_overlong_token(self):
        token = 'ddddeeeeaaaaddddbbbbeeeeeeeefffff'
        assert csrf._sanitize_token(token) is None

    def test_st_rejects_underlong_token(self):
        token = 'ddddeeeeaaaaddddbbbbeeeeeeeefff'
        assert csrf._sanitize_token(token) is None

    def test_st_rejects_goofy_token(self):
        token = 'ddddeeeeaaaadddd bbbbeeeeeeeefff'
        assert csrf._sanitize_token(token) is None


    # integration tests

    def test_no_csrf_cookie_gives_403(self):
        r = self.client.POST('/', csrf_token=False, raise_immediately=False)
        assert r.code == 403
        assert "Bad CSRF cookie" in r.body
        assert b'csrf_token' in r.headers.cookie

    def test_bad_csrf_cookie_gives_403(self):
        r = self.client.POST('/', csrf_token=b'bad_token', raise_immediately=False)
        assert r.code == 403
        assert "Bad CSRF cookie" in r.body
        assert r.headers.cookie[b'csrf_token'].value != 'bad_token'

    def test_csrf_cookie_set_for_most_requests(self):
        r = self.client.GET('/about/')
        assert b'csrf_token' in r.headers.cookie

    def test_no_csrf_cookie_set_for_assets(self):
        r = self.client.GET('/assets/gratipay.css')
        assert b'csrf_token' not in r.headers.cookie
