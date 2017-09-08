# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import uuid as uuidlib
from postgres.orm import Model


class PaymentForOpenSource(Model):

    typname = "payments_for_open_source"

    def __repr__(self):
        return '<PaymentForOpenSource: %s>'.format(repr(self.amount))


    @classmethod
    def from_uuid(cls, uuid, cursor=None):
        return (cursor or cls.db).one("""
            SELECT pfos.*::payments_for_open_source
              FROM payments_for_open_source pfos
             WHERE uuid = %s
        """, (uuid,))


    @classmethod
    def insert(cls, amount, transaction_id, name, follow_up, email_address, message_id,
               promotion_name, promotion_url, promotion_twitter, promotion_message,
               cursor=None):
        uuid = uuidlib.uuid4().hex
        return (cursor or cls.db).one("""
            INSERT INTO payments_for_open_source
                        (uuid, amount, transaction_id, name, follow_up, email_address, message_id,
                         promotion_name, promotion_url, promotion_twitter, promotion_message)
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
              RETURNING payments_for_open_source.*::payments_for_open_source
        """, (uuid, amount, transaction_id, name, follow_up, email_address, message_id,
              promotion_name, promotion_url, promotion_twitter, promotion_message))
