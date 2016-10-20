from __future__ import print_function, unicode_literals

import datetime

import pytest

from gratipay.testing import Harness, D
from gratipay.utils import fake_data


class DateTime(datetime.datetime): pass
datetime.datetime = DateTime


class TestChartOfReceiving(Harness):
    def setUp(self):
        Harness.setUp(self)
        for participant in ['alice', 'bob']:
            p = self.make_participant(participant, claimed_time='now', last_bill_result='')
            setattr(self, participant, p)

    @pytest.mark.xfail(reason="#3399")
    def test_get_tip_distribution_handles_a_tip(self):
        self.alice.set_tip_to(self.bob, '3.00')
        expected = ([[D('3.00'), 1, D('3.00'), 1.0, D('1')]],
                    1.0, D('3.00'))
        actual = self.bob.get_tip_distribution()
        assert actual == expected

    @pytest.mark.xfail(reason="#3399")
    def test_get_tip_distribution_handles_no_tips(self):
        expected = ([], 0.0, D('0.00'))
        actual = self.alice.get_tip_distribution()
        assert actual == expected

    @pytest.mark.xfail(reason="#3399")
    def test_get_tip_distribution_handles_multiple_tips(self):
        carl = self.make_participant('carl', claimed_time='now', last_bill_result='')
        self.alice.set_tip_to(self.bob, '1.00')
        carl.set_tip_to(self.bob, '3.00')
        expected = ([
            [D('1.00'), 1L, D('1.00'), 0.5, D('0.25')],
            [D('3.00'), 1L, D('3.00'), 0.5, D('0.75')]
        ], 2.0, D('4.00'))
        actual = self.bob.get_tip_distribution()
        assert actual == expected

    @pytest.mark.xfail(reason="#3399")
    def test_get_tip_distribution_handles_big_tips(self):
        self.bob.update_number('plural')
        carl = self.make_participant('carl', claimed_time='now', last_bill_result='')
        self.alice.set_tip_to(self.bob, '200.00')
        carl.set_tip_to(self.bob, '300.00')
        expected = ([
            [D('200.00'), 1L, D('200.00'), 0.5, D('0.4')],
            [D('300.00'), 1L, D('300.00'), 0.5, D('0.6')]
        ], 2.0, D('500.00'))
        actual = self.bob.get_tip_distribution()
        assert actual == expected

    @pytest.mark.xfail(reason="#3399")
    def test_get_tip_distribution_ignores_bad_cc(self):
        bad_cc = self.make_participant('bad_cc', claimed_time='now', last_bill_result='Failure!')
        self.alice.set_tip_to(self.bob, '1.00')
        bad_cc.set_tip_to(self.bob, '3.00')
        expected = ([[D('1.00'), 1L, D('1.00'), 1, D('1')]],
                    1.0, D('1.00'))
        actual = self.bob.get_tip_distribution()
        assert actual == expected

    @pytest.mark.xfail(reason="#3399")
    def test_get_tip_distribution_ignores_missing_cc(self):
        missing_cc = self.make_participant('missing_cc', claimed_time='now')
        self.alice.set_tip_to(self.bob, '1.00')
        missing_cc.set_tip_to(self.bob, '3.00')
        expected = ([[D('1.00'), 1L, D('1.00'), 1, D('1')]],
                    1.0, D('1.00'))
        actual = self.bob.get_tip_distribution()
        assert actual == expected


class TestHtml(Harness):
    def test_200(self):
        fake_data.populate_db(self.db, 5, 5, 1)
        response = self.client.GET('/about/stats')
        assert response.code == 200
