# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import gratipay
import uuid as uuidlib
from postgres.orm import Model


class PaymentForOpenSource(Model):

    typname = "payments_for_open_source"

    def __repr__(self):
        return '<PaymentForOpenSource: %s>'.format(repr(self.amount))


    @property
    def receipt_url(self):
        return '{}/browse/payments/{}.html'.format(gratipay.base_url, self.uuid)


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
    def insert(cls, amount, name, follow_up, email_address,
               promotion_name, promotion_url, promotion_twitter, promotion_message,
               cursor=None):
        """Take baseline info and insert into the database.
        """
        uuid = uuidlib.uuid4().hex
        return (cursor or cls.db).one("""
            INSERT INTO payments_for_open_source
                        (uuid, amount, name, follow_up, email_address,
                         promotion_name, promotion_url, promotion_twitter, promotion_message)
                 VALUES (%s, %s, %s, %s, %s,
                         %s, %s, %s, %s)
              RETURNING payments_for_open_source.*::payments_for_open_source
        """, (uuid, amount, name, follow_up, email_address,
              promotion_name, promotion_url, promotion_twitter, promotion_message))


    def process_result(self, result):
        """Take a Braintree API result and update the database.
        """
        transaction_id = result.transaction.id if result.transaction else None
        self.db.run("""
            UPDATE payments_for_open_source
               SET transaction_id=%s
                 , succeeded=%s
             WHERE uuid=%s
        """, (transaction_id, result.is_success, self.uuid))
        self.set_attributes(transaction_id=transaction_id, succeeded=result.is_success)
