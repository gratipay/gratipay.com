# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.models.package import NPM, Package
from gratipay.testing import Harness


class Tests(Harness):

	def test_filter_by_approved(self):
        self.make_team(is_approved=True)
        assert 'The Enterprise' in self.client.GET("/?status=approved").body

    def test_filter_by_unreviewed(self):
        self.make_team(is_approved=None)
        assert 'The Enterprise' in self.client.GET("/?status=unreviewed").body

    def test_filter_by_rejected(self):
        self.make_team(is_approved=False)
        assert 'The Enterprise' in self.client.GET("/?status=rejected").body
