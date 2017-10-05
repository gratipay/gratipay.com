# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from uuid import uuid4

import gratipay
from aspen import Response
from postgres.orm import Model

from ..utils import images


class PaymentForOpenSource(Model, images.HasImage):

    typname = "payments_for_open_source"
    singular = "payment_for_open_source"

    def __repr__(self):
        return '<PaymentForOpenSource: {}>'.format(repr(self.amount))


    @property
    def succeeded(self):
        return self.braintree_result_message == ''


    @property
    def url_path(self):
        return '/browse/payments/{}/'.format(self.id)


    @property
    def invoice_url(self):
        if not self.succeeded:
            return None
        return '{}{}invoice.html?secret={}'.format(gratipay.base_url, self.url_path, self.secret)


    @classmethod
    def from_id(cls, id, cursor=None):
        """Take an id and return an object.
        """
        return (cursor or cls.db).one("""
            SELECT pfos.*::payments_for_open_source
              FROM payments_for_open_source pfos
             WHERE id = %s
        """, (id,))


    @classmethod
    def insert(cls, amount, name, on_mailing_list, email_address,
               promotion_name, promotion_url, promotion_twitter, promotion_message,
               cursor=None):
        """Take baseline info and insert into the database.
        """
        secret = uuid4().hex
        on_mailing_list = on_mailing_list == 'yes'
        return (cursor or cls.db).one("""
            INSERT INTO payments_for_open_source
                        (secret, amount, name, on_mailing_list, email_address,
                         promotion_name, promotion_url, promotion_twitter, promotion_message)
                 VALUES (%s, %s, %s, %s, %s,
                         %s, %s, %s, %s)
              RETURNING payments_for_open_source.*::payments_for_open_source
        """, (secret, amount, name, on_mailing_list, email_address,
              promotion_name, promotion_url, promotion_twitter, promotion_message))


    def process_result(self, result):
        """Take a Braintree API result and update the database.
        """
        result_message = '' if result.is_success else result.message
        transaction_id = None
        if result.transaction:
            transaction_id = result.transaction.id

            # Verify that Braintree is sending us the right payload.
            # TODO This is hard to test and it should be a pretty tight guarantee,
            # so I am commenting out for now. :(
            #pfos_id = result.transaction.custom_fields['pfos_id']
            #assert pfos_id == self.id, (pfos_id, transaction_id)

        self.db.run("""
            UPDATE payments_for_open_source
               SET braintree_result_message=%s
                 , braintree_transaction_id=%s
             WHERE id=%s
        """, (result_message, transaction_id, self.id))
        self.set_attributes( braintree_result_message=result_message
                           , braintree_transaction_id=transaction_id
                            )


def cast(path_part, state):
    """This is an Aspen typecaster. Given an id and a state dict, raise
    Response or return PaymentForOpenSource.
    """
    try:
        pfos = PaymentForOpenSource.from_id(path_part)
    except:
        raise Response(404)
    if pfos is None:
        raise Response(404)
    return pfos
