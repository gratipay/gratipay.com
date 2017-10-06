# -*- coding: utf-8 -*-
"""This is the Python library behind gratipay.com.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay import utils
from gratipay.utils import images
from gratipay.models.payment_for_open_source import PaymentForOpenSource


kB = 2**10


def _parse(raw):
    """Given a POST request.body, return (parsed<dict>, errors<list>).
    """

    errors = []
    x = lambda f: raw[f].strip()  # KeyError -> 400

    # payment info
    amount = x('amount')
    if (not amount.isdigit()) or (int(amount) < 10):
        errors.append('amount')
        amount = ''.join(x for x in amount.split('.')[0] if x.isdigit())

    payment_method_nonce = x('payment_method_nonce')
    if len(payment_method_nonce) > 36:
        errors.append('payment_method_nonce')
        payment_method_nonce = ''

    # contact info
    name = x('name')
    if len(name) > 255:
        name = name[:255]
        errors.append('name')

    email_address = x('email_address')
    if email_address and not utils.is_valid_email_address(email_address):
        email_address = email_address[:255]
        errors.append('email_address')

    on_mailing_list = x('on_mailing_list')
    if on_mailing_list not in ('yes', 'no'):
        on_mailing_list = 'yes'
        errors.append('on_mailing_list')

    # promo fields
    promotion_logo = None
    _logo = raw['promotion_logo']
    if _logo.value:
        if _logo.type not in ('image/png', 'image/jpeg'):
            errors.append('promotion_logo')
        else:
            try:
                original = _logo.value
                large, small = images.imgize(original, _logo.type)
                promotion_logo = (original, large, small, _logo.type)
            except images.BadImage:
                errors.append('promotion_logo')

    promotion_name = x('promotion_name')
    if len(promotion_name) > 32:
        promotion_name = promotion_name[:32]
        errors.append('promotion_name')

    promotion_url = x('promotion_url')
    is_link = lambda x: (x.startswith('http://') or x.startswith('https://')) and '.' in x
    if len(promotion_url) > 255 or (promotion_url and not is_link(promotion_url)):
        promotion_url = promotion_url[:255]
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
             , 'on_mailing_list': on_mailing_list
             , 'promotion_logo': promotion_logo
             , 'promotion_name': promotion_name
             , 'promotion_url': promotion_url
             , 'promotion_twitter': promotion_twitter
             , 'promotion_message': promotion_message
              }
    return parsed, errors


def _store(parsed):
    logo = parsed.pop('promotion_logo')
    pfos = PaymentForOpenSource.insert(**parsed)
    if logo:
        pfos.save_image(*logo)
    return pfos


def _charge(app, pfos, nonce):
    params = { 'amount': pfos.amount
             , 'payment_method_nonce': nonce
             , 'options': {'submit_for_settlement': True}
             , 'custom_fields': {'pfos_id': pfos.id}
              }
    result = app.pfos_card_charger.charge(params)
    pfos.process_result(result)


def _send(app, pfos):
    app.email_queue.put( to=None
                       , template='paid-for-open-source'
                       , email=pfos.email_address
                       , amount=pfos.amount
                       , invoice_url=pfos.invoice_url
                        )


def pay_for_open_source(app, raw):
    parsed, errors = _parse(raw)
    out = {'errors': errors, 'invoice_url': None}
    if not errors:
        payment_method_nonce = parsed.pop('payment_method_nonce')
        pfos = _store(parsed)
        _charge(app, pfos, payment_method_nonce)
        if pfos.succeeded:
            out['invoice_url'] = pfos.invoice_url
            if pfos.email_address:
                _send(app, pfos)
        else:
            out['errors'].append('charging')
    return out


def get_latest_pfos(app):
    return app.db.one("""

    SELECT pfos.*::payments_for_open_source
      FROM payments_for_open_source pfos
     WHERE braintree_result_message = ''
  ORDER BY ctime DESC
     LIMIT 1
          ;

    """)
