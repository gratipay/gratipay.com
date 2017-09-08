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
