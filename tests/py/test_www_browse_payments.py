# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing import Harness


class Tests(Harness):

    def make_payments(self):
        for i in xrange(1, 21):
            self.make_payment_for_open_source(promotion_name='A-{} Widgets, Inc.'.format(i))

    def test_first_page_is_shown_by_default(self):
        self.make_payments()
        homepage = self.client.GET("/browse/payments/").body
        assert 'A-20 Widgets, Inc.' in homepage
        assert 'A-11 Widgets, Inc.' in homepage
        assert 'A-10 Widgets, Inc.' not in homepage
        assert 'A-9 Widgets, Inc.' not in homepage

    def test_page_filter_works(self):
        self.make_payments()
        homepage = self.client.GET("/browse/payments/?page=2").body
        assert 'A-20 Widgets, Inc.' not in homepage
        assert 'A-11 Widgets, Inc.' not in homepage
        assert 'A-10 Widgets, Inc.' in homepage
        assert 'A-9 Widgets, Inc.' in homepage

    def test_invalid_page_filter_does_not_blow_up(self):
        self.client.GET("/browse/payments/?page=abcd") # Should not throw an exception

    def test_out_of_bounds_page_filter_renders_zero_payments(self):
        self.make_payments()
        homepage = self.client.GET("/browse/payments/?page=500").body
        assert 'Widgets, Inc.' not in homepage
