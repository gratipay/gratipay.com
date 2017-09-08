# -*- coding: utf-8 -*-
"""This is the Python library behind gratipay.com.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import braintree
from gratipay import utils
from gratipay.models.payment_for_open_source import PaymentForOpenSource


def _parse(raw):
    """Given a POST request.body, return (parsed<dict>, errors<list>).
    """

    errors = []
    x = lambda f: raw.get(f, '').strip()

    # amount
    amount = x('amount') or '0'
    if (not amount.isdigit()) or (int(amount) < 10):
        errors.append('amount')
        amount = ''.join(x for x in amount.split('.')[0] if x.isdigit())

    # credit card nonce
    payment_method_nonce = x('payment_method_nonce')
    if len(payment_method_nonce) > 36:
        errors.append('payment_method_nonce')
        payment_method_nonce = ''

    # name
    name = x('name')
    if len(name) > 256:
        name = name[:256]
        errors.append('name')

    # email address
    email_address = x('email_address')
    if email_address and not utils.is_valid_email_address(email_address):
        email_address = email_address[:255]
        errors.append('email_address')

    # follow_up
    follow_up = x('follow_up')
    if follow_up not in ('monthly', 'quarterly', 'yearly', 'never'):
        follow_up = 'monthly'
        errors.append('follow_up')

    promotion_name = x('promotion_name')
    if len(promotion_name) > 32:
        promotion_name = promotion_name[:32]
        errors.append('promotion_name')

    promotion_url = x('promotion_url')
    is_link = lambda x: (x.startswith('http://') or x.startswith('https://')) and '.' in x
    if len(promotion_url) > 256 or not is_link(promotion_url):
        promotion_url = promotion_url[:256]
        errors.append('promotion_url')

    promotion_twitter = x('promotion_twitter')
    if len(promotion_twitter) > 32:
        promotion_twitter = promotion_twitter[:32]
        # TODO What are Twitter's rules?
        errors.append('promotion_twitter')

    promotion_message = x('promotion_message')
    if len(promotion_message) > 128:
        promotion_message = promotion_message[:128]
        errors.append('promotion_message')

    parsed = { 'amount': amount
             , 'payment_method_nonce': payment_method_nonce
             , 'name': name
             , 'email_address': email_address
             , 'follow_up': follow_up
             , 'promotion_name': promotion_name
             , 'promotion_url': promotion_url
             , 'promotion_twitter': promotion_twitter
             , 'promotion_message': promotion_message
              }
    return parsed, errors


def _store(parsed):
    return PaymentForOpenSource.insert(**parsed)


def _charge(amount, payment_method_nonce, _sale=braintree.Transaction.sale):
    return _sale({ 'amount': amount
                 , 'payment_method_nonce': payment_method_nonce
                 , 'options': {'submit_for_settlement': True}
                  })


def _send(app, email_address, payment_for_open_source):
    app.email_queue.put( to=None
                       , template='paid-for-open-source'
                       , email=email_address
                       , amount=payment_for_open_source.amount
                       , receipt_url=payment_for_open_source.receipt_url
                        )


def pay_for_open_source(app, raw):
    parsed, errors = _parse(raw)
    payment_method_nonce = parsed.pop('payment_method_nonce')
    payment_for_open_source = _store(parsed)
    if not errors:
        result = _charge(parsed['amount'], payment_method_nonce)
        payment_for_open_source.process_result(result)
        if not payment_for_open_source.succeeded:
            errors.append('charging')
    if not errors and parsed['email_address']:
        _send(app, parsed['email_address'], payment_for_open_source)
        parsed = {}  # no need to populate form anymore
    return {'parsed': parsed, 'errors': errors}
