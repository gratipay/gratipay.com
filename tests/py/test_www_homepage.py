# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import urllib

import aspen.body_parsers
from gratipay.homepage import pay_for_open_source, _parse, _store, _send
from gratipay.testing import Harness
from gratipay.testing.email import QueuedEmailHarness
from pytest import raises


_oh_yeah = lambda *a: 'oh yeah'
_none = lambda *a: None


GOOD = { 'amount': '1000'
       , 'name': 'Alice Liddell'
       , 'email_address': 'alice@example.com'
       , 'follow_up': 'monthly'
       , 'promotion_name': 'Wonderland'
       , 'promotion_url': 'http://www.example.com/'
       , 'promotion_twitter': 'thebestbutter'
       , 'promotion_message': 'Love me! Love me! Say that you love me!'
        }
BAD = { 'amount': '1,000'
      , 'name': 'Alice Liddell' * 20
      , 'email_address': 'alice' * 100 + '@example.com'
      , 'follow_up': 'cheese'
      , 'promotion_name': 'Wonderland' * 100
      , 'promotion_url': 'http://www.example.com/' + 'cheese' * 100
      , 'promotion_twitter': 'thebestbutter' * 10
      , 'promotion_message': 'Love me!' * 50
       }
SCRUBBED = { 'amount': '1000'
           , 'name': 'Alice Liddell' * 19 + 'Alice Lid'
           , 'email_address': 'alice' * 51
           , 'follow_up': 'monthly'
           , 'promotion_name': 'WonderlandWonderlandWonderlandWo'
           , 'promotion_url': 'http://www.example.com/' + 'cheese' * 38 + 'chees'
           , 'promotion_twitter': 'thebestbutterthebestbutterthebes'
           , 'promotion_message': 'Love me!' * 16
            }
ALL = ['amount', 'name', 'email_address', 'follow_up',
       'promotion_name', 'promotion_url', 'promotion_twitter', 'promotion_message']


class Parse(Harness):

    def test_good_values_survive(self):
        parsed, errors = _parse(GOOD)
        assert parsed == GOOD
        assert errors == []

    def test_bad_values_get_scrubbed_and_flagged(self):
        parsed, errors = _parse(BAD)
        assert parsed == SCRUBBED
        assert errors == ALL


class Store(Harness):

    def test_stores_info(self):
        parsed, errors = _parse(GOOD)
        fetch = lambda: self.db.one('SELECT * FROM payments_for_open_source')
        assert fetch() is None
        _store(parsed, 'deadbeef')
        assert fetch().follow_up == 'monthly'


class Send(QueuedEmailHarness):

    def test_sends_receipt_link(self):
        parsed, errors = _parse(GOOD)
        payment_for_open_source = _store(parsed, 'deadbeef')
        _send(self.app, parsed, payment_for_open_source)
        msg = self.get_last_email()
        assert msg['to'] == 'alice@example.com'
        assert msg['subject'] == 'Payment for open source'


class PayForOpenSource(Harness):

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
        fetch = lambda: self.db.one('SELECT * FROM payments_for_open_source')
        assert fetch() is None
        result = pay_for_open_source(self.app, self.good, _charge=_oh_yeah, _send=_none)
        assert result == {'parsed': {}, 'errors': ['sending']}  # TODO revisit once we have _send
        assert fetch().transaction_id == 'oh yeah'

    def test_scrubs_and_flags_errors_and_doesnt_store(self):
        fetch = lambda: self.db.one('SELECT * FROM payments_for_open_source')
        assert fetch() is None
        result = pay_for_open_source(self.app, self.bad, _charge=_oh_yeah, _send=_none)
        assert result == {'parsed': SCRUBBED, 'errors': ALL}
        assert fetch() is None


    def test_post_gets_json(self):
        with raises(NotImplementedError):
            self.client.POST('/', data=GOOD)
