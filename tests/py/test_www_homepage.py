# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.homepage import _parse
from gratipay.testing import Harness


class Parse(Harness):

    def test_good_values_survive(self):
        parsed, errors = _parse({ 'amount': '1000'
                                , 'name': 'Alice Liddell'
                                , 'email_address': 'alice@example.com'
                                , 'follow_up': 'monthly'
                                , 'promotion_name': 'Wonderland'
                                , 'promotion_url': 'http://www.example.com/'
                                , 'promotion_twitter': 'thebestbutter'
                                , 'promotion_message': 'Love me! Love me! Say that you love me!'
                                 })
        assert parsed == { 'amount': '1000'
                         , 'name': 'Alice Liddell'
                         , 'email_address': 'alice@example.com'
                         , 'follow_up': 'monthly'
                         , 'promotion_name': 'Wonderland'
                         , 'promotion_url': 'http://www.example.com/'
                         , 'promotion_twitter': 'thebestbutter'
                         , 'promotion_message': 'Love me! Love me! Say that you love me!'
                          }
        assert errors == []


    def test_bad_values_get_scrubbed_and_flagged(self):
        parsed, errors = _parse({ 'amount': '1,000'
                                , 'name': 'Alice Liddell' * 20
                                , 'email_address': 'alice' * 100 + '@example.com'
                                , 'follow_up': 'cheese'
                                , 'promotion_name': 'Wonderland' * 100
                                , 'promotion_url': 'http://www.example.com/' + 'cheese' * 100
                                , 'promotion_twitter': 'thebestbutter' * 10
                                , 'promotion_message': 'Love me!' * 50
                                 })
        assert parsed == { 'amount': '1000'
                         , 'name': 'Alice Liddell' * 19 + 'Alice Lid'
                         , 'email_address': 'alice' * 51
                         , 'follow_up': 'monthly'
                         , 'promotion_name': 'WonderlandWonderlandWonderlandWo'
                         , 'promotion_url': 'http://www.example.com/' + 'cheese' * 38 + 'chees'
                         , 'promotion_twitter': 'thebestbutterthebestbutterthebes'
                         , 'promotion_message': 'Love me!' * 16
                          }
        assert errors == ['amount', 'name', 'email_address', 'follow_up', 'promotion_name',
                          'promotion_url', 'promotion_twitter', 'promotion_message']
