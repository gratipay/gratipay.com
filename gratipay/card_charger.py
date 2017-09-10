# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import braintree
from uuid import uuid4
from decimal import Decimal as D


class CardCharger(object):

    def __init__(self, online=False):
        self.implementation = Braintree() if online else FakeBraintree()

    def charge(self, params):
        return self.implementation.charge(params)


# Online
# ======

class Braintree(object):
    """Sends data to Braintree.
    """

    def charge(self, params):
        """Charge using the Braintree APi, returning a result.
        """
        return braintree.Transaction.sale(params)


# Offline
# =======

class FakeTransaction(object):
    def __init__(self):
        self.id = uuid4().hex

class FakeSuccessResult(object):
    def __init__(self):
        self.is_success = True
        self.transaction = FakeTransaction()

class FakeFailureResult(object):
    def __init__(self):
        self.is_success = False
        self.message = 'Not a success.'
        self.transaction = FakeTransaction()

class FakeErrorResult(object):
    def __init__(self):
        self.is_success = False
        self.message = 'Not even a success.'
        self.transaction = None


class FakeBraintree(object):
    """For offline use.
    """

    def charge(self, params):
        """Return a fake result. Partially implements Braintree's testing logic:

        - fake-valid-nonce returns a success result
        - amount >= 2000 returns a failure result
        - otherwise return an error result

        https://developers.braintreepayments.com/reference/general/testing/python

        """
        if params['payment_method_nonce'] == 'fake-valid-nonce':
            if D(params['amount']) < 2000:
                return FakeSuccessResult()
            return FakeFailureResult()
        return FakeErrorResult()
