# -*- coding: utf-8 -*-
"""This is the Python library behind gratipay.com.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay import utils


def pay_for_open_source(app, raw):
    parsed, errors = _parse(raw)
    if not errors:
        transaction_id = _charge_card(app, parsed)
        if not transaction_id:
            errors.append('charge_card')
    if not errors:
        message_id = None
        if parsed['email_address']:
            message_id = _send_receipt(app, parsed['email_address'])
            if not message_id:
                errors.append('send_receipt')
        _store_info(parsed, transaction_id, message_id)
        parsed = {}
    return {'parsed': parsed, 'errors': errors}


def _parse(raw):
    """Given a POST request.body, return (parsed<dict>, errors<list>).
    """

    errors = []
    x = lambda f: raw.get(f, '').strip()

    # amount
    amount = x('amount') or '0'
    if (not amount.isdigit()) or (int(amount) < 50):
        errors.append('amount')
        amount = ''.join(x for x in amount.split('.')[0] if x.isdigit())

    # TODO credit card token?

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
             , 'name': name
             , 'email_address': email_address
             , 'follow_up': follow_up
             , 'promotion_name': promotion_name
             , 'promotion_url': promotion_url
             , 'promotion_twitter': promotion_twitter
             , 'promotion_message': promotion_message
              }
    return parsed, errors


def _charge_card(app, parsed):
    raise NotImplementedError


def _send_receipt(app, parsed):
    raise NotImplementedError
    app.email_queue.put()


def _store_info(parsed, transaction_id, message_id):
    raise NotImplementedError

