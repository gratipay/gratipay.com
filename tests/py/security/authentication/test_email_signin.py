# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from uuid import UUID

from gratipay.models.participant.email import AUTH_VALID, AUTH_INVALID, AUTH_EXPIRED
from gratipay.testing import Harness


class Base(Harness):

    def setUp(self):
        self.alice = self.make_participant('alice')
        self.add_and_verify_email(self.alice, 'alice@gratipay.com')


class TestCreateSigninNonce(Base):

    def _fetch_rec_from_db(self, nonce):
        return self.db.one("SELECT * FROM email_auth_nonces WHERE nonce = %s", (nonce, ), back_as=dict)

    def test_inserts_into_db(self):
        nonce = self.alice.create_signin_nonce('alice@gratipay.com')
        rec = self._fetch_rec_from_db(nonce)

        assert rec['nonce'] == nonce
        assert rec['intent'] == 'sign-in'
        assert rec['email_address'] == 'alice@gratipay.com'

    def test_nonce_is_valid_uuid(self):
        nonce = self.alice.create_signin_nonce('alice@gratipay.com')

        assert UUID(nonce, version=4).__class__ == UUID


class TestVerifyNonce(Base):

    def test_valid_nonce(self):
        nonce = self.alice.create_signin_nonce('alice@gratipay.com')
        assert self.alice.verify_nonce('alice@gratipay.com', nonce) == AUTH_VALID

    def test_expired_nonce(self):
        nonce = self.alice.create_signin_nonce('alice@gratipay.com')
        self.db.run("UPDATE email_auth_nonces SET ctime = ctime - interval '1 day'")
        assert self.alice.verify_nonce('alice@gratipay.com', nonce) == AUTH_EXPIRED

    def test_invalid_nonce(self):
        self.alice.create_signin_nonce('alice@gratipay.com')
        assert self.alice.verify_nonce('alice@gratipay.com', "dummy_nonce") == AUTH_INVALID


class TestInvalidateNonce(Base):

    def test_deletes_nonce(self):
        nonce = self.alice.create_signin_nonce('alice@gratipay.com')
        self.alice.invalidate_nonce('alice@gratipay.com', nonce)

        assert self.alice.verify_nonce('alice@gratipay.com', nonce) == AUTH_INVALID

    def test_only_deletes_one_nonce(self):
        nonce1 = self.alice.create_signin_nonce('alice@gratipay.com')
        nonce2 = self.alice.create_signin_nonce('alice@gratipay.com')
        self.alice.invalidate_nonce('alice@gratipay.com', nonce1)

        assert self.alice.verify_nonce('alice@gratipay.com', nonce1) == AUTH_INVALID
        assert self.alice.verify_nonce('alice@gratipay.com', nonce2) == AUTH_VALID

    def test_tolerates_invalidated_nonce(self):
        nonce = self.alice.create_signin_nonce('alice@gratipay.com')
        self.alice.invalidate_nonce('alice@gratipay.com', nonce)
        self.alice.invalidate_nonce('alice@gratipay.com', nonce) # Should not throw an error
