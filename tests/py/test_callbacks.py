from __future__ import absolute_import, division, print_function, unicode_literals

import json

from decimal import Decimal as D
from mock import patch

from gratipay.billing.exchanges import record_exchange
from gratipay.models.exchange_route import ExchangeRoute
from gratipay.testing import Harness


class TestBalancedCallbacks(Harness):

    def callback(self, *a, **kw):
        kw.setdefault(b'HTTP_X_FORWARDED_FOR', b'50.18.199.26')
        kw.setdefault('content_type', 'application/json')
        kw.setdefault('raise_immediately', False)
        return self.client.POST('/callbacks/balanced', **kw)

    def test_simplate_checks_source_address(self):
        r = self.callback(HTTP_X_FORWARDED_FOR=b'0.0.0.0')
        assert r.code == 403

    def test_simplate_doesnt_require_a_csrf_token(self):
        r = self.callback(body=b'{"events": []}', csrf_token=False)
        assert r.code == 200, r.body

    def test_no_csrf_cookie_set_for_callbacks(self):
        r = self.callback(body=b'{"events": []}', csrf_token=False)
        assert b'csrf_token' not in r.headers.cookie

    @patch('gratipay.billing.exchanges.record_exchange_result')
    def test_credit_callback(self, rer):
        alice = self.make_participant('alice', last_ach_result='', balance=100)
        ba = ExchangeRoute.from_network(alice, 'balanced-ba')
        for status in ('succeeded', 'failed'):
            error = 'FOO' if status == 'failed' else None
            e_id = record_exchange(self.db, ba, -10, 0, alice, 'pre')
            body = json.dumps({
                "events": [
                    {
                        "type": "credit."+status,
                        "entity": {
                            "credits": [
                                {
                                    "failure_reason": error,
                                    "meta": {
                                        "participant_id": alice.id,
                                        "exchange_id": e_id,
                                    },
                                    "status": status,
                                }
                            ]
                        }
                    }
                ]
            })
            r = self.callback(body=body, csrf_token=False)
            assert r.code == 200, r.body
            assert rer.call_count == 1
            assert rer.call_args[0][:-1] == (self.db, e_id, status, error)
            assert rer.call_args[0][-1].id == alice.id
            assert rer.call_args[1] == {}
            rer.reset_mock()

class TestCoinbaseCallback(Harness):

    def payload(self, participant):
        return {
            "order": {
                "id": "10N9LK1Q",
                "event": {
                    "type": "completed"
                },
                "total_native": {
                    "cents": 100,
                    "currency_iso": "USD"
                },
                "total_payout": {
                    "cents": 99,
                    "currency_iso": "USD"
                },
                "custom": participant.id,
            }
        }

    def callback(self, *a, **kw):
        kw.setdefault('csrf_token', False)
        kw.setdefault('content_type', 'application/json')
        kw.setdefault('raise_immediately', False)

        secret_key = kw.pop('secret_key', self.client.website.coinbase_secret_key)
        url = '/callbacks/coinbase?secret_key=%s' % secret_key

        return self.client.POST(url, **kw)

    def test_simplate_checks_secret_key(self):
        r = self.callback(body=b'{}', secret_key='wrong_key')
        assert r.code == 401, r.body

    def test_simplate_doesnt_require_a_csrf_token(self):
        r = self.callback(body=b'{}', csrf_token=False)
        assert r.code == 200, r.body

    def test_no_csrf_cookie_set_for_callbacks(self):
        r = self.callback(body=b'{}', csrf_token=False)
        assert b'csrf_token' not in r.headers.cookie

    @patch('gratipay.billing.exchanges.record_exchange')
    @patch('gratipay.billing.exchanges.record_exchange_result')
    def test_coinbase_success_callback(self, rer, re):
        re.return_value == 12345
        alice = self.make_participant('alice')
        body = json.dumps(self.payload(alice))

        r = self.callback(body=body)
        assert r.code == 200, r.body

        # Must create a route
        route = ExchangeRoute.from_address(alice, 'coinbase-payin', '10N9LK1Q')
        assert isinstance(route, ExchangeRoute)

        assert re.call_count == rer.call_count ==  1

        assert re.call_args[0][0] == self.db
        assert re.call_args[0][1].id == route.id
        assert re.call_args[0][2:4] == (D('0.99'), D('0.01')) # Amount, Fee
        assert re.call_args[0][4].id == alice.id
        assert re.call_args[0][5] == 'pre' # Status

        assert rer.call_args[0][0:4] == (self.db, re.return_value, 'succeeded', None)
        assert rer.call_args[0][4].id == alice.id

    @patch('gratipay.billing.exchanges.record_exchange')
    @patch('gratipay.billing.exchanges.record_exchange_result')
    def test_coinbase_callback_reuses_route_if_exists(self, rer, re):
        alice = self.make_participant('alice')
        body = json.dumps(self.payload(alice))

        # Route exists before callback
        route = ExchangeRoute.insert(alice, 'coinbase-payin', '10N9LK1Q')

        self.callback(body=body)

        # Make sure it reuses the route
        assert re.call_args[0][1].id == route.id
