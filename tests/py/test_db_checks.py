# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay import models
from gratipay.testing import Harness


class Tests(Harness):

    # cb - _check_balances - calls assert so we don't need asserts here

    def test_cb_is_fine_with_empty_database(self):
        with self.db.get_cursor() as cursor:
            models._check_balances(cursor)

    def test_cb_is_fine_with_status_unknown(self):
        self.make_team()
        alice = self.make_participant('alice')
        self.make_exchange('braintree-cc', 12, 0, alice, status='unknown')
        self.db.run('INSERT INTO payments (participant, team, amount, direction) '
                    "VALUES ('alice', 'TheEnterprise', 11, 'to-team')")

        # force expected balance - unknown doesn't update balance, and we don't
        # have a good make_payment to do it for us either
        self.db.run("UPDATE participants SET balance=1 WHERE username='alice'")

        with self.db.get_cursor() as cursor:
            models._check_balances(cursor)
