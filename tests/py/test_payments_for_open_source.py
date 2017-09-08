# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing import Harness
from gratipay.models.payment_for_open_source import PaymentForOpenSource


class Tests(Harness):

    def test_can_insert(self):
        self.make_payment_for_open_source()
        assert self.db.one('SELECT * FROM payments_for_open_source').name == 'Alice Liddell'

    def test_can_fetch(self):
        uuid = self.make_payment_for_open_source().uuid
        assert PaymentForOpenSource.from_uuid(uuid).name == 'Alice Liddell'

    def test_can_update(self):
        pfos = self.make_payment_for_open_source()
        assert pfos.transaction_id is None
        assert not pfos.succeeded

        class Transaction:
            id = 'deadbeef'
        class Result:
            transaction = Transaction()
            is_success = True
        result = Result()

        pfos.process_result(result)
        assert pfos.transaction_id == 'deadbeef'
        assert pfos.succeeded

        fresh = self.db.one("SELECT * FROM payments_for_open_source")
        assert fresh.transaction_id == 'deadbeef'
        assert fresh.succeeded
