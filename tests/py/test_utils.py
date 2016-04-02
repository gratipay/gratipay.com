from __future__ import absolute_import, division, print_function, unicode_literals

from datetime import datetime, timedelta
from decimal import Decimal as D

import pytest
from aspen.http.response import Response
from gratipay import utils
from gratipay.testing import Harness
from gratipay.utils import i18n, markdown, pricing, encode_for_querystring, decode_from_querystring
from gratipay.utils.username import safely_reserve_a_username, FailedToReserveUsername, \
                                                                           RanOutOfUsernameAttempts
from psycopg2 import IntegrityError


class Tests(Harness):

    def test_get_team_gets_team(self):
        team = self.make_team()
        state = self.client.GET( '/TheEnterprise/'
                               , return_after='dispatch_request_to_filesystem'
                               , want='state'
                                )
        assert utils.get_team(state) == team

    def test_get_team_canonicalizes(self):
        self.make_team()
        state = self.client.GET( '/theenterprise/'
                               , return_after='dispatch_request_to_filesystem'
                               , want='state'
                                )

        with self.assertRaises(Response) as cm:
            utils.get_team(state)
        assert cm.exception.code == 302
        assert cm.exception.headers['Location'] == '/TheEnterprise/'

    def test_get_participant_gets_participant(self):
        expected = self.make_participant('alice', claimed_time='now')
        state = self.client.GET( '/~alice/'
                               , return_after='dispatch_request_to_filesystem'
                               , want='state'
                                )
        actual = utils.get_participant(state, restrict=False)
        assert actual == expected

    def test_get_participant_canonicalizes(self):
        self.make_participant('alice', claimed_time='now')
        state = self.client.GET( '/~Alice/'
                               , return_after='dispatch_request_to_filesystem'
                               , want='state'
                                )

        with self.assertRaises(Response) as cm:
            utils.get_participant(state, restrict=False)
        assert cm.exception.code == 302
        assert cm.exception.headers['Location'] == '/~/alice/'

    def test_dict_to_querystring_converts_dict_to_querystring(self):
        expected = "?foo=bar"
        actual = utils.dict_to_querystring({"foo": ["bar"]})
        assert actual == expected

    def test_dict_to_querystring_converts_empty_dict_to_querystring(self):
        expected = ""
        actual = utils.dict_to_querystring({})
        assert actual == expected

    def test_short_difference_is_expiring(self):
        expiring = datetime.utcnow() + timedelta(days = 1)
        expiring = utils.is_card_expiring(expiring.year, expiring.month)
        assert expiring

    def test_long_difference_not_expiring(self):
        expiring = datetime.utcnow() + timedelta(days = 100)
        expiring = utils.is_card_expiring(expiring.year, expiring.month)
        assert not expiring

    def test_format_currency_without_trailing_zeroes(self):
        expected = '$16'
        actual = i18n.format_currency_with_options(16, 'USD', locale='en', trailing_zeroes=False)
        assert actual == expected

    def test_format_currency_with_trailing_zeroes(self):
        expected = '$16.00'
        actual = i18n.format_currency_with_options(16, 'USD', locale='en', trailing_zeroes=True)
        assert actual == expected

    def test_format_currency_defaults_to_trailing_zeroes(self):
        expected = '$16.00'
        actual = i18n.format_currency_with_options(16, 'USD', locale='en')
        assert actual == expected


    # sru - safely_reserve_a_username

    def test_srau_safely_reserves_a_username(self):
        def gen_test_username():
            yield 'deadbeef'
        def reserve(cursor, username):
            return 'deadbeef'
        with self.db.get_cursor() as cursor:
            username = safely_reserve_a_username(cursor, gen_test_username, reserve)
        assert username == 'deadbeef'
        assert self.db.one('SELECT username FROM participants') is None

    def test_srau_inserts_a_participant_by_default(self):
        def gen_test_username():
            yield 'deadbeef'
        with self.db.get_cursor() as cursor:
            username = safely_reserve_a_username(cursor, gen_test_username)
        assert username == 'deadbeef'
        assert self.db.one('SELECT username FROM participants') == 'deadbeef'

    def test_srau_wears_a_seatbelt(self):
        def gen_test_username():
            for i in range(101):
                yield 'deadbeef'
        def reserve(cursor, username):
            raise IntegrityError
        with self.db.get_cursor() as cursor:
            with pytest.raises(FailedToReserveUsername):
                safely_reserve_a_username(cursor, gen_test_username, reserve)

    def test_srau_seatbelt_goes_to_100(self):
        def gen_test_username():
            for i in range(100):
                yield 'deadbeef'
        def reserve(cursor, username):
            raise IntegrityError
        with self.db.get_cursor() as cursor:
            with pytest.raises(RanOutOfUsernameAttempts):
                safely_reserve_a_username(cursor, gen_test_username, reserve)

    def test_markdown_render_does_render(self):
        expected = "<p>Example</p>\n"
        actual = markdown.render('Example')
        assert expected == actual

    def test_markdown_render_escapes_scripts(self):
        expected = '<p>Example alert &ldquo;hi&rdquo;;</p>\n'
        actual = markdown.render('Example <script>alert "hi";</script>')
        assert expected == actual

    def test_markdown_render_renders_http_links(self):
        expected = '<p><a href="http://example.com/">foo</a></p>\n'
        assert markdown.render('[foo](http://example.com/)') == expected
        expected = '<p><a href="http://example.com/">http://example.com/</a></p>\n'
        assert markdown.render('<http://example.com/>') == expected

    def test_markdown_render_renders_https_links(self):
        expected = '<p><a href="https://example.com/">foo</a></p>\n'
        assert markdown.render('[foo](https://example.com/)') == expected
        expected = '<p><a href="https://example.com/">https://example.com/</a></p>\n'
        assert markdown.render('<https://example.com/>') == expected

    def test_markdown_render_escapes_javascript_links(self):
        expected = '<p>[foo](javascript:foo)</p>\n'
        assert markdown.render('[foo](javascript:foo)') == expected
        expected = '<p>&lt;javascript:foo&gt;</p>\n'
        assert markdown.render('<javascript:foo>') == expected

    def test_markdown_render_doesnt_allow_any_explicit_anchors(self):
        expected = '<p>foo</p>\n'
        assert markdown.render('<a href="http://example.com/">foo</a>') == expected
        expected = '<p>foo</p>\n'
        assert markdown.render('<a href="https://example.com/">foo</a>') == expected
        expected = '<p>foo</p>\n'
        assert markdown.render('<a href="javascript:foo">foo</a>') == expected

    def test_markdown_render_autolinks(self):
        expected = '<p><a href="http://google.com/">http://google.com/</a></p>\n'
        actual = markdown.render('http://google.com/')
        assert expected == actual

    def test_markdown_render_no_intra_emphasis(self):
        expected = '<p>Examples like this_one and this other_one.</p>\n'
        actual = markdown.render('Examples like this_one and this other_one.')
        assert expected == actual

    def test_srau_retries_work_with_db(self):
        self.make_participant('deadbeef')
        def gen_test_username():
            yield 'deadbeef'
            yield 'deafbeef'
        with self.db.get_cursor() as cursor:
            username = safely_reserve_a_username(cursor, gen_test_username)
            assert username == 'deafbeef'


    # sp - suggested_payment

    def test_sp_suggests_five_dollars_on_100(self):
        assert pricing.suggested_payment(100) == D('5')

    def test_sp_suggests_fifty_cents_on_10_dollars(self):
        assert pricing.suggested_payment(10) == D('0.5')

    def test_sp_suggests_five_cents_on_1_dollar(self):
        assert pricing.suggested_payment(1) == D('0.05')

    def test_sp_rounds_to_nearest_five_cents(self):
        assert pricing.suggested_payment(D('98.33')) == D('4.90')


    # splh - suggested_payment_low_high

    def test_splh_suggests_five_dollars_and_ten_on_100(self):
        assert pricing.suggested_payment_low_high(100) == (D('5'), D('10'))

    def test_splh_suggests_fifty_cents_and_a_dollar_on_10_dollars(self):
        assert pricing.suggested_payment_low_high(10) == (D('0.5'), D('1'))

    def test_splh_suggests_five_and_ten_cents_on_1_dollar(self):
        assert pricing.suggested_payment_low_high(1) == (D('0.05'), D('0.1'))

    def test_splh_rounds_to_nearest_five_cents(self):
        assert pricing.suggested_payment_low_high(D('98.33')) == (D('4.90'), D('9.85'))


    # querystring encoding/decoding
    # =============================

    # efq = encode_for_querystring

    def test_efq_replaces_slash_with_underscore(self):
        # TheEnter?prise => VGhlRW50ZXI/cHJpc2U=
        assert encode_for_querystring('TheEnter?prise') == 'VGhlRW50ZXI_cHJpc2U~'

    def test_efq_replaces_equals_with_tilde(self):
        assert encode_for_querystring('TheEnterprise') == 'VGhlRW50ZXJwcmlzZQ~~'


    # dfq - decode_from_querystring

    def test_dfq_decodes(self):
        assert decode_from_querystring('VGhlRW50ZXI_cHJpc2U~') == 'TheEnter?prise'

    def test_dfq_raises_response_on_error(self):
        with self.assertRaises(Response) as cm:
            decode_from_querystring('abcd')
        assert cm.exception.code == 400

    def test_dfq_returns_default_if_passed_on_error(self):
        assert decode_from_querystring('abcd', default='error') == 'error'
