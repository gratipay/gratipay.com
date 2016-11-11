# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.security import csrf


class Tests(object):

    def test_sanitize_token_passes_through_good_token(self):
        token = 'ddddeeeeaaaaddddbbbbeeeeeeeeffff'
        assert csrf._sanitize_token(token) == token

    def test_sanitize_token_rejects_overlong_token(self):
        token = 'ddddeeeeaaaaddddbbbbeeeeeeeefffff'
        assert csrf._sanitize_token(token) is None

    def test_sanitize_token_rejects_underlong_token(self):
        token = 'ddddeeeeaaaaddddbbbbeeeeeeeefff'
        assert csrf._sanitize_token(token) is None

    def test_sanitize_token_rejects_goofy_token(self):
        token = 'ddddeeeeaaaadddd bbbbeeeeeeeefff'
        assert csrf._sanitize_token(token) is None
