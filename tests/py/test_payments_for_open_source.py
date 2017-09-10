# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.homepage import _charge
from gratipay.models.payment_for_open_source import PaymentForOpenSource
from gratipay.testing import Harness


class TestPaymentForOpenSource(Harness):

    def test_can_insert(self):
        self.make_payment_for_open_source()
        assert self.db.one('SELECT * FROM payments_for_open_source').name == 'Alice Liddell'

    def test_can_fetch(self):
        uuid = self.make_payment_for_open_source().uuid
        assert PaymentForOpenSource.from_uuid(uuid).name == 'Alice Liddell'

    def test_can_update(self):
        pfos = self.make_payment_for_open_source()
        assert pfos.braintree_transaction_id is None
        assert pfos.braintree_result_message is None
        assert not pfos.succeeded

        _charge(self.app, pfos, 'fake-valid-nonce')

        assert pfos.braintree_transaction_id is not None
        assert pfos.braintree_result_message == ''
        assert pfos.succeeded

        fresh = self.db.one("SELECT pfos.*::payments_for_open_source "
                            "FROM payments_for_open_source pfos")
        assert fresh.braintree_transaction_id is not None
        assert fresh.braintree_result_message == ''
        assert fresh.succeeded
