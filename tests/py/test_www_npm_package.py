# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing import Harness


class TestAnon(Harness):

    def setUp(self):
        self.make_package()

    def test_gets_signin_page(self):
        assert 'npm/foo</a> has not been claimed' in self.client.GET('/on/npm/foo/').body
