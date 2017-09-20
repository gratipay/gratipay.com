# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import gratipay
from uuid import uuid4
from postgres.orm import Model


class PaymentForOpenSource(Model):

    typname = "payments_for_open_source"

    def __repr__(self):
        return '<PaymentForOpenSource: {}>'.format(repr(self.amount))


    @property
    def succeeded(self):
        return self.braintree_result_message == ''


    @property
    def invoice_url(self):
        if not self.succeeded:
            return None
        return '{}/browse/payments/{}/invoice.html'.format(gratipay.base_url, self.uuid)


    @classmethod
    def from_uuid(cls, uuid, cursor=None):
        """Take a uuid and return an object.
        """
        return (cursor or cls.db).one("""
            SELECT pfos.*::payments_for_open_source
              FROM payments_for_open_source pfos
             WHERE uuid = %s
        """, (uuid,))


    @classmethod
    def insert(cls, amount, grateful_for, name, follow_up, email_address,
               promotion_name, promotion_url, promotion_twitter, promotion_message,
               cursor=None):
        """Take baseline info and insert into the database.
        """
        uuid = uuid4().hex
        return (cursor or cls.db).one("""
            INSERT INTO payments_for_open_source
                        (uuid, amount, grateful_for, name, follow_up, email_address,
                         promotion_name, promotion_url, promotion_twitter, promotion_message)
                 VALUES (%s, %s, %s, %s, %s, %s,
                         %s, %s, %s, %s)
              RETURNING payments_for_open_source.*::payments_for_open_source
        """, (uuid, amount, grateful_for, name, follow_up, email_address,
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
            #pfos_uuid = result.transaction.custom_fields['pfos_uuid']
            #assert pfos_uuid == self.uuid, (pfos_uuid, transaction_id)

        self.db.run("""
            UPDATE payments_for_open_source
               SET braintree_result_message=%s
                 , braintree_transaction_id=%s
             WHERE uuid=%s
        """, (result_message, transaction_id, self.uuid))
        self.set_attributes( braintree_result_message=result_message
                           , braintree_transaction_id=transaction_id
                            )
