# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals
from uuid import UUID

from gratipay.security.authentication.email import create_nonce, verify_nonce, invalidate_nonce
from gratipay.security.authentication.email import NONCE_VALID, NONCE_INVALID, NONCE_EXPIRED
from gratipay.testing import Harness

class TestCreateNonce(Harness):

    def setUp(self):
        alice = self.make_participant('alice')
        self.add_and_verify_email(alice, 'alice@gratipay.com')

    def _fetch_rec_from_db(self, nonce):
        return self.db.one("SELECT * FROM email_auth_nonces WHERE nonce = %s", (nonce, ), back_as=dict)

    def test_inserts_into_db(self):
        nonce = create_nonce(self.db, 'alice@gratipay.com')
        rec = self._fetch_rec_from_db(nonce)

        assert rec['nonce'] == nonce
        assert rec['email_address'] == 'alice@gratipay.com'

    def test_nonce_is_valid_uuid(self):
        nonce = create_nonce(self.db, 'alice@gratipay.com')

        assert UUID(nonce, version=4).__class__ == UUID


class TestVerifyNonce(Harness):

    def setUp(self):
        alice = self.make_participant('alice')
        self.add_and_verify_email(alice, 'alice@gratipay.com')

    def test_valid_nonce(self):
        nonce = create_nonce(self.db, 'alice@gratipay.com')
        assert verify_nonce(self.db, 'alice@gratipay.com',  nonce) == NONCE_VALID

    def test_expired_nonce(self):
        nonce = create_nonce(self.db, 'alice@gratipay.com')
        self.db.run("UPDATE email_auth_nonces SET ctime = ctime - interval '1 day'")
        assert verify_nonce(self.db, 'alice@gratipay.com',  nonce) == NONCE_EXPIRED

    def test_invalid_nonce(self):
        create_nonce(self.db, 'alice@gratipay.com')
        assert verify_nonce(self.db, 'alice@gratipay.com',  "dummy_nonce") == NONCE_INVALID

class TestInvalidateNonce(Harness):

    def setUp(self):
        alice = self.make_participant('alice')
        self.add_and_verify_email(alice, 'alice@gratipay.com')

    def test_deletes_nonce(self):
        nonce = create_nonce(self.db, 'alice@gratipay.com')
        invalidate_nonce(self.db, 'alice@gratipay.com', nonce)

        assert verify_nonce(self.db, 'alice@gratipay.com', nonce) == NONCE_INVALID

    def test_only_deletes_one_nonce(self):
        nonce1 = create_nonce(self.db, 'alice@gratipay.com')
        nonce2 = create_nonce(self.db, 'alice@gratipay.com')
        invalidate_nonce(self.db, 'alice@gratipay.com', nonce1)

        assert verify_nonce(self.db, 'alice@gratipay.com', nonce1) == NONCE_INVALID
        assert verify_nonce(self.db, 'alice@gratipay.com', nonce2) == NONCE_VALID

    def test_tolerates_invalidated_nonce(self):
        nonce = create_nonce(self.db, 'alice@gratipay.com')
        invalidate_nonce(self.db, 'alice@gratipay.com', nonce)
        invalidate_nonce(self.db, 'alice@gratipay.com', nonce) # Should not throw an error
