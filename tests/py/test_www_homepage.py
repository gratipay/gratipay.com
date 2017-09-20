# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import json
import urllib

import aspen.body_parsers
from gratipay.homepage import pay_for_open_source, _parse, _store, _charge, _send
from gratipay.testing import Harness
from gratipay.testing.email import QueuedEmailHarness


_oh_yeah = lambda *a: 'oh yeah'
_none = lambda *a: None


GOOD = { 'amount': '1000'
       , 'payment_method_nonce': 'fake-valid-nonce'
       , 'grateful_for': 'python, javascript'
       , 'name': 'Alice Liddell'
       , 'email_address': 'alice@example.com'
       , 'follow_up': 'monthly'
       , 'promotion_name': 'Wonderland'
       , 'promotion_url': 'http://www.example.com/'
       , 'promotion_twitter': 'thebestbutter'
       , 'promotion_message': 'Love me! Love me! Say that you love me!'
        }
BAD = { 'amount': '1,000'
      , 'payment_method_nonce': 'deadbeef' * 5
      , 'grateful_for': 'x' * (16 * 2**10) + 'x'
      , 'name': 'Alice Liddell' * 20
      , 'email_address': 'alice' * 100 + '@example.com'
      , 'follow_up': 'cheese'
      , 'promotion_name': 'Wonderland' * 100
      , 'promotion_url': 'http://www.example.com/' + 'cheese' * 100
      , 'promotion_twitter': 'thebestbutter' * 10
      , 'promotion_message': 'Love me!' * 50
       }
PARTIAL = { 'amount': '1000'
          , 'payment_method_nonce': 'fake-valid-nonce'
          , 'grateful_for': ''
          , 'name': ''
          , 'email_address': ''
          , 'follow_up': 'quarterly'
          , 'promotion_name': ''
          , 'promotion_url': ''
          , 'promotion_twitter': ''
          , 'promotion_message': ''
           }
SCRUBBED = { 'amount': '1000'
           , 'payment_method_nonce': ''
           , 'grateful_for': 'x' * (16 * 2**10)
           , 'name': 'Alice Liddell' * 19 + 'Alice Li'
           , 'email_address': 'alice' * 51
           , 'follow_up': 'monthly'
           , 'promotion_name': 'WonderlandWonderlandWonderlandWo'
           , 'promotion_url': 'http://www.example.com/' + 'cheese' * 38 + 'chee'
           , 'promotion_twitter': 'thebestbutterthebestbutterthebes'
           , 'promotion_message': 'Love me!' * 16
            }
ALL = ['amount', 'payment_method_nonce', 'grateful_for', 'name', 'email_address', 'follow_up',
       'promotion_name', 'promotion_url', 'promotion_twitter', 'promotion_message']


class PayForOpenSourceHarness(Harness):

    def fetch(self):
        return self.db.one('SELECT pfos.*::payments_for_open_source '
                           'FROM payments_for_open_source pfos')


class Parse(Harness):

    def test_good_values_survive(self):
        parsed, errors = _parse(GOOD)
        assert parsed == GOOD
        assert errors == []

    def test_bad_values_get_scrubbed_and_flagged(self):
        parsed, errors = _parse(BAD)
        assert parsed == SCRUBBED
        assert errors == ALL

    def test_partial_info_is_fine(self):
        parsed, errors = _parse(PARTIAL)
        assert parsed == PARTIAL
        assert errors == []

    def test_10_dollar_minimum(self):
        bad = GOOD.copy()
        bad['amount'] = '9'
        assert _parse(bad)[1] == ['amount']

        good = GOOD.copy()
        good['amount'] = '10'
        assert _parse(good)[1] == []


# Valid nonces for testing:
# https://developers.braintreepayments.com/reference/general/testing/python#valid-nonces
#
# Separate classes to force separate fixtures to avoid conflation. #2588
# suggests we don't want to match on body for some reason? Hacking here vs.
# getting to the bottom of that.

class GoodCharge(Harness):

    def test_bad_nonce_fails(self):
        pfos = self.make_payment_for_open_source()
        _charge(self.app, pfos, 'deadbeef')
        assert not pfos.succeeded

class BadCharge(Harness):

    def test_good_nonce_succeeds(self):
        pfos = self.make_payment_for_open_source()
        _charge(self.app, pfos, 'fake-valid-nonce')
        assert pfos.succeeded


class Store(PayForOpenSourceHarness):

    def test_stores_info(self):
        parsed, errors = _parse(GOOD)
        parsed.pop('payment_method_nonce')
        assert self.fetch() is None
        _store(parsed)
        assert self.fetch().follow_up == 'monthly'


class Send(QueuedEmailHarness):

    def test_sends_invoice_link(self):
        parsed, errors = _parse(GOOD)
        parsed.pop('payment_method_nonce')
        payment_for_open_source = _store(parsed)
        _send(self.app, payment_for_open_source)
        msg = self.get_last_email()
        assert msg['to'] == 'alice@example.com'
        assert msg['subject'] == 'Invoice from Gratipay'


class PayForOpenSource(PayForOpenSourceHarness):

    def as_body(self, **raw):
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        encoded = urllib.urlencode(raw)
        return aspen.body_parsers.formdata(encoded, headers)

    @property
    def good(self):
        return self.as_body(**GOOD)

    @property
    def bad(self):
        return self.as_body(**BAD)

    def test_pays_for_open_source(self):
        assert self.fetch() is None
        result = pay_for_open_source(self.app, self.good)
        assert not result['errors']
        assert result['invoice_url'].endswith('invoice.html')
        assert self.fetch().succeeded

    def test_flags_errors_and_doesnt_store(self):
        assert self.fetch() is None
        result = pay_for_open_source(self.app, self.bad)
        assert result == {'errors': ALL, 'invoice_url': None}
        assert self.fetch() is None

    def test_flags_errors_with_no_transaction_id(self):
        error = GOOD.copy()
        error['payment_method_nonce'] = 'deadbeef'
        result = pay_for_open_source(self.app, error)
        assert result['errors'] == ['charging']
        pfos = self.fetch()
        assert not pfos.succeeded
        assert pfos.braintree_transaction_id is None

    def test_flags_failures_with_transaction_id(self):
        failure = GOOD.copy()
        failure['amount'] = '2000'
        result = pay_for_open_source(self.app, failure)
        assert result['errors'] == ['charging']
        pfos = self.fetch()
        assert not pfos.succeeded
        assert pfos.braintree_transaction_id is not None


    def test_post_gets_json(self):
        response = self.client.POST('/', data=GOOD, HTTP_ACCEPT=b'application/json')
        assert response.code == 200
        assert response.headers['Content-Type'] == 'application/json'
        result = json.loads(response.body)
        assert not result['errors']
        assert result['invoice_url'].endswith('invoice.html')
        assert self.fetch().succeeded

    def test_bad_post_gets_400(self):
        response = self.client.POST('/', data=BAD, HTTP_ACCEPT=b'application/json')
        assert response.code == 200  # :(
        assert response.headers['Content-Type'] == 'application/json'
        assert json.loads(response.body)['errors'] == ALL

    def test_really_bad_post_gets_plain_400(self):
        response = self.client.PxST('/', data={}, HTTP_ACCEPT=b'application/json')
        assert response.code == 400
        assert response.headers == {}
        assert response.body == "Missing key: u'amount'"


class PartialPost(PayForOpenSourceHarness):  # separate class to work around wiring issues

    def test_partial_post_is_fine(self):
        response = self.client.POST('/', data=PARTIAL, HTTP_ACCEPT=b'application/json')
        assert response.code == 200
        assert response.headers['Content-Type'] == 'application/json'
        result = json.loads(response.body)
        assert not result['errors']
        assert result['invoice_url'].endswith('invoice.html')
        assert self.fetch().succeeded
