# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing import Harness


class Tests(Harness):

    # Filtering

    def test_filter_by_approved(self):
        self.make_team(is_approved=True)
        assert 'The Enterprise' in self.client.GET("/browse/projects?status=approved").body

    def test_filter_by_unreviewed(self):
        self.make_team(is_approved=None)
        assert 'The Enterprise' in self.client.GET("/browse/projects?status=unreviewed").body

    def test_filter_by_rejected(self):
        self.make_team(is_approved=False)
        assert 'The Enterprise' in self.client.GET("/browse/projects?status=rejected").body

    # Pagination

    def test_first_page_is_shown_by_default(self):
        for i in xrange(1, 21):
            self.make_team(is_approved=True, name='Gratiteam ' + str(i))

        homepage = self.client.GET("/browse/projects?status=approved").body

        assert 'Gratiteam 20' in homepage
        assert 'Gratiteam 11' in homepage
        assert 'Gratiteam 10' not in homepage
        assert 'Gratiteam 9' not in homepage

    def test_page_filter_works(self):
        for i in xrange(1, 21):
            self.make_team(is_approved=True, name='Gratiteam ' + str(i))

        homepage = self.client.GET("/browse/projects?status=approved&page=2").body

        assert 'Gratiteam 20' not in homepage
        assert 'Gratiteam 11' not in homepage
        assert 'Gratiteam 10' in homepage
        assert 'Gratiteam 9'  in homepage

    def test_invalid_page_filter_does_not_blow_up(self):
        self.client.GET("/browse/projects?status=approved&page=abcd") # Should not throw an exception

    def test_out_of_bounds_page_filter_renders_zero_projects(self):
        for i in xrange(1, 5):
            self.make_team(is_approved=True, name='Gratiteam ' + str(i))

        homepage = self.client.GET("/browse/projects?status=approved&page=500").body

        assert 'Gratiteam' not in homepage


