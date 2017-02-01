# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from datetime import datetime, timedelta

import pytest
from aspen.http.response import Response
from gratipay import utils
from gratipay.testing import Harness, D
from gratipay.utils import i18n, pricing, encode_for_querystring, decode_from_querystring, \
                                                                    truncate, get_featured_projects
from gratipay.utils.username import safely_reserve_a_username, FailedToReserveUsername, \
                                                                           RanOutOfUsernameAttempts
from psycopg2 import IntegrityError


class TestGetTeam(Harness):

    def test_gets_team(self):
        team = self.make_team()
        state = self.client.GET( '/TheEnterprise/'
                               , return_after='dispatch_request_to_filesystem'
                               , want='state'
                                )
        assert utils.get_team(state) == team

    def test_canonicalizes(self):
        self.make_team()
        state = self.client.GET( '/theenterprise/'
                               , return_after='dispatch_request_to_filesystem'
                               , want='state'
                                )

        with self.assertRaises(Response) as cm:
            utils.get_team(state)
        assert cm.exception.code == 302
        assert cm.exception.headers['Location'] == '/TheEnterprise/'


class TestGetParticipant(Harness):

    def test_gets_participant(self):
        expected = self.make_participant('alice', claimed_time='now')
        state = self.client.GET( '/~alice/'
                               , return_after='dispatch_request_to_filesystem'
                               , want='state'
                                )
        actual = utils.get_participant(state, restrict=False)
        assert actual == expected

    def test_canonicalizes(self):
        self.make_participant('alice', claimed_time='now')
        state = self.client.GET( '/~Alice/'
                               , return_after='dispatch_request_to_filesystem'
                               , want='state'
                                )

        with self.assertRaises(Response) as cm:
            utils.get_participant(state, restrict=False)
        assert cm.exception.code == 302
        assert cm.exception.headers['Location'] == '/~/alice/'


class TestDictToQuerystring(Harness):

    def test_converts_dict_to_querystring(self):
        expected = "?foo=bar"
        actual = utils.dict_to_querystring({"foo": ["bar"]})
        assert actual == expected

    def test_converts_empty_dict_to_querystring(self):
        expected = ""
        actual = utils.dict_to_querystring({})
        assert actual == expected


class TestIsCardExpiring(Harness):

    def test_short_difference_is_expiring(self):
        expiring = datetime.utcnow() + timedelta(days = 1)
        expiring = utils.is_card_expiring(expiring.year, expiring.month)
        assert expiring

    def test_long_difference_not_expiring(self):
        expiring = datetime.utcnow() + timedelta(days = 100)
        expiring = utils.is_card_expiring(expiring.year, expiring.month)
        assert not expiring


class TestFormatCurrentcyWithOptions(Harness):

    def test_formats_currency_without_trailing_zeroes(self):
        expected = '$16'
        actual = i18n.format_currency_with_options(16, 'USD', locale='en', trailing_zeroes=False)
        assert actual == expected

    def test_formats_currency_with_trailing_zeroes(self):
        expected = '$16.00'
        actual = i18n.format_currency_with_options(16, 'USD', locale='en', trailing_zeroes=True)
        assert actual == expected

    def test_defaults_to_trailing_zeroes(self):
        expected = '$16.00'
        actual = i18n.format_currency_with_options(16, 'USD', locale='en')
        assert actual == expected


class TestSafelyReserveAUsername(Harness):

    def test_safely_reserves_a_username(self):
        def gen_test_username():
            yield 'deadbeef'
        def reserve(cursor, username):
            return 'deadbeef'
        with self.db.get_cursor() as cursor:
            username = safely_reserve_a_username(cursor, gen_test_username, reserve)
        assert username == 'deadbeef'
        assert self.db.one('SELECT username FROM participants') is None

    def test_inserts_a_participant_by_default(self):
        def gen_test_username():
            yield 'deadbeef'
        with self.db.get_cursor() as cursor:
            username = safely_reserve_a_username(cursor, gen_test_username)
        assert username == 'deadbeef'
        assert self.db.one('SELECT username FROM participants') == 'deadbeef'

    def test_wears_a_seatbelt(self):
        def gen_test_username():
            for i in range(101):
                yield 'deadbeef'
        def reserve(cursor, username):
            raise IntegrityError
        with self.db.get_cursor() as cursor:
            with pytest.raises(FailedToReserveUsername):
                safely_reserve_a_username(cursor, gen_test_username, reserve)

    def test_seatbelt_goes_to_100(self):
        def gen_test_username():
            for i in range(100):
                yield 'deadbeef'
        def reserve(cursor, username):
            raise IntegrityError
        with self.db.get_cursor() as cursor:
            with pytest.raises(RanOutOfUsernameAttempts):
                safely_reserve_a_username(cursor, gen_test_username, reserve)

    def test_retries_work_with_db(self):
        self.make_participant('deadbeef')
        def gen_test_username():
            yield 'deadbeef'
            yield 'deafbeef'
        with self.db.get_cursor() as cursor:
            username = safely_reserve_a_username(cursor, gen_test_username)
            assert username == 'deafbeef'


class TestSuggestedPayment(Harness):

    def test_suggests_five_dollars_on_100(self):
        assert pricing.suggested_payment(100) == D('5')

    def test_suggests_fifty_cents_on_10_dollars(self):
        assert pricing.suggested_payment(10) == D('0.5')

    def test_suggests_five_cents_on_1_dollar(self):
        assert pricing.suggested_payment(1) == D('0.05')

    def test_rounds_to_nearest_five_cents(self):
        assert pricing.suggested_payment(D('98.33')) == D('4.90')


class TestSuggestedPaymentLowHigh(Harness):

    def test_suggests_five_dollars_and_ten_on_100(self):
        assert pricing.suggested_payment_low_high(100) == (D('5'), D('10'))

    def test_suggests_fifty_cents_and_a_dollar_on_10_dollars(self):
        assert pricing.suggested_payment_low_high(10) == (D('0.5'), D('1'))

    def test_suggests_five_and_ten_cents_on_1_dollar(self):
        assert pricing.suggested_payment_low_high(1) == (D('0.05'), D('0.1'))

    def test_rounds_to_nearest_five_cents(self):
        assert pricing.suggested_payment_low_high(D('98.33')) == (D('4.90'), D('9.85'))


class TestEncodeForQuerystring(Harness):

    def test_replaces_slash_with_underscore(self):
        # TheEnter?prise => VGhlRW50ZXI/cHJpc2U=
        assert encode_for_querystring('TheEnter?prise') == 'VGhlRW50ZXI_cHJpc2U~'

    def test_replaces_equals_with_tilde(self):
        assert encode_for_querystring('TheEnterprise') == 'VGhlRW50ZXJwcmlzZQ~~'

    def test_doesnt_accept_bytes(self):
        with self.assertRaises(TypeError):
            encode_for_querystring(b'TheEnterprise')


class TestDecodeFromQuerystring(Harness):

    def test_decodes_properly(self):
        assert decode_from_querystring('VGhlRW50ZXI_cHJpc2U~') == 'TheEnter?prise'
        assert decode_from_querystring('VGhlRW50ZXJwcmlzZQ~~') == 'TheEnterprise'

    def test_doesnt_accept_bytes(self):
        with self.assertRaises(TypeError):
            decode_from_querystring(b'VGhlRW50ZXI_cHJpc2U~')

    def test_raises_response_on_error(self):
        with self.assertRaises(Response) as cm:
            decode_from_querystring('abcd')
        assert cm.exception.code == 400

    def test_returns_default_if_passed_on_error(self):
        assert decode_from_querystring('abcd', default='error') == 'error'


class TestTruncate(Harness):

    def test_truncates(self):
        assert truncate('I am a long sentence.', 13) == 'I am a long …'

    def test_doesnt_split_words(self):
        assert truncate('I am a long sentence.', 16) == 'I am a long …'

    def test_finds_word_break_properly(self):
        assert truncate('I am a long sentence.', 12) == 'I am a …'
        assert truncate('I am a long sentence.', 14) == 'I am a long …'

    def test_splits_words_if_it_has_to(self):
        assert truncate('I_am_a_long_sentence.', 17) == 'I_am_a_long_sen …'

    def test_returns_whole_thing_if_possible(self):
        assert truncate('I am a long sentence.', 20) == 'I am a long …'
        assert truncate('I am a long sentence.', 21) == 'I am a long sentence.'
        assert truncate('I am a long sentence.', 22) == 'I am a long sentence.'
        assert truncate('I am a long sentence.', 220000) == 'I am a long sentence.'

    def test_appends_what_you_like(self):
        assert truncate('I am a long sentence.', 14, ' cheese.') == 'I am a cheese.'

    def test_lets_appending_take_over(self):
        assert truncate('I am a long sentence.', 21, ' the cheese!') == 'I am a long sentence.'
        assert truncate('I am a long sentence.', 20, ' the cheese!') == 'I am a the cheese!'
        assert truncate('I am a long sentence.', 19, ' the cheese!') == 'I am a the cheese!'
        assert truncate('I am a long sentence.', 18, ' the cheese!') == 'I am a the cheese!'
        assert truncate('I am a long sentence.', 17, ' the cheese!') == 'I am the cheese!'
        assert truncate('I am a long sentence.', 16, ' the cheese!') == 'I am the cheese!'
        assert truncate('I am a long sentence.', 15, ' the cheese!') == 'I the cheese!'
        assert truncate('I am a long sentence.', 14, ' the cheese!') == 'I the cheese!'
        assert truncate('I am a long sentence.', 13, ' the cheese!') == 'I the cheese!'
        assert truncate('I am a long sentence.', 12, ' the cheese!') == ' the cheese!'
        assert truncate('I am a long sentence.', 11, ' the cheese!') == ' the cheese!'
        assert truncate('I am a long sentence.', 10, ' the cheese!') == ' the cheese!'
        assert truncate('I am a long sentence.',  9, ' the cheese!') == ' the cheese!'
        assert truncate('I am a long sentence.',  8, ' the cheese!') == ' the cheese!'
        assert truncate('I am a long sentence.',  7, ' the cheese!') == ' the cheese!'
        assert truncate('I am a long sentence.',  6, ' the cheese!') == ' the cheese!'
        assert truncate('I am a long sentence.',  5, ' the cheese!') == ' the cheese!'
        assert truncate('I am a long sentence.',  4, ' the cheese!') == ' the cheese!'
        assert truncate('I am a long sentence.',  3, ' the cheese!') == ' the cheese!'
        assert truncate('I am a long sentence.',  2, ' the cheese!') == ' the cheese!'
        assert truncate('I am a long sentence.',  1, ' the cheese!') == ' the cheese!'
        assert truncate('I am a long sentence.',  0, ' the cheese!') == ' the cheese!'
        assert truncate('I am a long sentence.', -1, ' the cheese!') == ' the cheese!'
        assert truncate('I am a long sentence.', -1000, ' the cheese!') == ' the cheese!'


class TestGetFeaturedProjects(Harness):

    def get_and_count(self, popular, unpopular):
        featured = get_featured_projects(popular, unpopular)
        npopular = len([p for p in featured if type(p) is int])
        nunpopular = len([p for p in featured if type(p) is unicode])
        return npopular, nunpopular

    def test_includes_more_popular_than_unpopular(self):
        popular, unpopular = range(100), list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
        assert self.get_and_count(popular, unpopular) == (7, 3)

    def test_deals_with_zero_popular_projects(self):
        popular, unpopular = range(0), list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
        assert self.get_and_count(popular, unpopular) == (0, 10)

    def test_deals_with_some_but_too_few_popular_projects(self):
        popular, unpopular = range(6), list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
        assert self.get_and_count(popular, unpopular) == (6, 4)

    def test_deals_with_zero_unpopular_projects(self):
        assert self.get_and_count(range(100), list('')) == (10, 0)

    def test_deals_with_some_but_too_few_unpopular_projects(self):
        assert self.get_and_count(range(100), list('AB')) == (8, 2)

    def test_deals_with_zero_projects(self):
        assert self.get_and_count(range(0), list('')) == (0, 0)

    def test_deals_with_some_but_too_few_of_both(self):
        assert self.get_and_count(range(4), list('A')) == (4, 1)
