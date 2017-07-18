# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import json

from gratipay.security.authentication.email import create_nonce, verify_nonce, NONCE_INVALID
from gratipay.testing import Harness, P
from gratipay.testing.email import QueuedEmailHarness
from gratipay.utils import encode_for_querystring

class TestSendLink(Harness):
    def test_returns_json(self):
        self.make_participant('alice', email_address='alice@gratipay.com')
        response = self.client.POST('/auth/send-link.json', {'email_address': 'alice@gratipay.com'})

        message = json.loads(response.body)['message']
        assert message == "We've sent you a link to sign in. Please check your inbox."

    def test_only_allows_post(self):
        response = self.client.GxT('/auth/send-link.json')

        assert response.code == 405

    def test_400_for_no_email_address_parameter(self):
        response = self.client.PxST('/auth/send-link.json')

        assert response.code == 400

    def test_400_for_invalid_email(self):
        response = self.client.POST('/auth/send-link.json', {'email_address': 'dummy@gratipay.com'})

        message = json.loads(response.body)['message']
        assert message == "We've sent you a link to create an account. Please check your inbox."

class TestSendLinkEmail(QueuedEmailHarness):
    def test_sends_signin_email(self):
        self.make_participant('alice', email_address='alice@gratipay.com')
        self.client.POST('/auth/send-link.json', {'email_address': 'alice@gratipay.com'})

        assert self.get_last_email()['to'] == 'alice <alice@gratipay.com>'
        assert 'Click the link below to sign in to Gratipay' in self.get_last_email()['body_text']
        assert 'Click the button below to sign in to Gratipay' in self.get_last_email()['body_html']

    def test_sends_signup_email(self):
        self.client.POST('/auth/send-link.json', {'email_address': 'new@gratipay.com'})

        assert self.get_last_email()['to'] == 'new@gratipay.com'
        assert 'Click the link below to create an account on Gratipay' in self.get_last_email()['body_text']
        assert 'Click the button below to create an account on Gratipay' in self.get_last_email()['body_html']


class TestVerify(Harness):
    def setUp(self):
        self.make_participant('alice', email_address='alice@gratipay.com')
        self.nonce = create_nonce(self.db, 'alice@gratipay.com')

    def test_400_if_nonce_not_provided(self):
        response = self.client.GxT('/auth/verify.html?email=abcd')
        assert response.code == 400
        assert response.body == '`nonce` parameter must be provided'

    def test_400_if_email_not_provided(self):
        response = self.client.GxT('/auth/verify.html?nonce=abcd')
        assert response.code == 400
        assert response.body == '`email` parameter must be provided'

    def test_redirects_on_success(self):
        link = self._get_link('alice@gratipay.com', self.nonce)
        response = self.client.GET(link, raise_immediately=False)

        assert response.code == 302
        assert response.headers['Location'] == '/'
        assert response.headers.cookie.get('session')

    def test_logs_in_on_success(self):
        link = self._get_link('alice@gratipay.com', self.nonce)
        response = self.client.GET(link, raise_immediately=False)

        assert response.headers.cookie.get('session')

    def test_invalidates_nonce_on_success(self):
        link = self._get_link('alice@gratipay.com', self.nonce)
        self.client.GET(link, raise_immediately=False)

        assert verify_nonce(self.db, 'alice@gratipay.com', self.nonce) == NONCE_INVALID

    def test_invalid_nonce(self):
        response = self.client.GET(self._get_link('alice@gratipay.com', 'dummy_nonce'))

        assert "Sorry, that's a bad link." in response.body

    def test_expired_nonce(self):
        self.db.run("UPDATE email_auth_nonces SET ctime = ctime - interval '1 day'")
        response = self.client.GET(self._get_link('alice@gratipay.com', self.nonce))

        assert "This link has expired. Please generate a new one." in response.body

    def _get_link(self, email, nonce):
        encoded_email = encode_for_querystring(email)

        return '/auth/verify.html?nonce=%s&email=%s' % (nonce, encoded_email)

class TestSignup(Harness):

    def test_400_if_nonce_not_provided(self):
        response = self.client.PxST('/auth/signup.json', {'email': 'abcd', 'username': 'abcd'})
        assert response.code == 400
        assert response.body == '`nonce` parameter must be provided'

    def test_400_if_username_not_provided(self):
        response = self.client.PxST('/auth/signup.json', {'email': 'abcd', 'nonce': 'abcd'})
        assert response.code == 400
        assert response.body == '`username` parameter must be provided'

    def test_400_if_email_not_provided(self):
        response = self.client.PxST('/auth/signup.json', {'username': 'abcd', 'nonce': 'abcd'})
        assert response.code == 400
        assert response.body == '`email` parameter must be provided'

    def test_creates_participant(self):
        nonce = create_nonce(self.db, 'alice@gratipay.com')
        response = self.client.POST('/auth/signup.json', {'username': 'alice',
                                                          'nonce': nonce,
                                                          'email': 'alice@gratipay.com'})

        assert response.code == 200
        assert P('alice')

    def test_returns_errors_with_username(self):
        self.make_participant('alice') # Username collission
        nonce = create_nonce(self.db, 'alice@gratipay.com')
        response = self.client.PxST('/auth/signup.json', {'username': 'alice',
                                                          'nonce': nonce,
                                                          'email': 'alice@gratipay.com'})

        assert response.code == 400
        assert response.body == "The username 'alice' is already taken."

    def test_returns_errors_with_nonce(self):
        response = self.client.PxST('/auth/signup.json', {'username': 'alice',
                                                          'nonce': 'invalid',
                                                          'email': 'alice@gratipay.com'})

        assert response.code == 400
        assert response.body == "This link is invalid."
