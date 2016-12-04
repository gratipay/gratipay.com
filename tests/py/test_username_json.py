# coding: utf8
from __future__ import print_function, unicode_literals

import json

from gratipay.testing import Harness


class Tests(Harness):

    def change_username(self, new_username, auth_as='alice'):
        if auth_as:
            self.make_participant(auth_as, claimed_time='now')

        r = self.client.POST('/~alice/username.json', {'username': new_username},
                             auth_as=auth_as, raise_immediately=False)
        return r.code, json.loads(r.body)

    def test_participant_can_change_their_username(self):
        code, body = self.change_username("bob")
        assert code == 200
        assert body['username'] == "bob"

    def test_anonymous_gets_401(self):
        code, body = self.change_username("bob", auth_as=None)
        assert code == 401

    def test_empty(self):
        code, body = self.change_username('      ')
        assert code == 400
        assert body['error_message_long'] == "You need to provide a username!"

    def test_invalid(self):
        code, body = self.change_username("§".encode('utf8'))
        assert code == 400
        assert body['error_message_long'] == "The username '§' contains invalid characters."

    def test_restricted_username_without_extension(self):
        code, body = self.change_username("assets")
        assert code == 400
        assert body['error_message_long'] == "The username 'assets' is restricted."

    def test_restricted_username_with_extension(self):
        code, body = self.change_username("1.0-payout")
        assert code == 400
        assert body['error_message_long'] == "The username '1.0-payout' is restricted."

    def test_robots_txt_is_not_an_available_username(self):
        code, body = self.change_username("robots.txt")
        assert code == 400
        assert body['error_message_long'] == "The username 'robots.txt' is restricted."

    def test_but_robots_txt_is_still_available_when_theres_a_robots_username(self):
        self.make_participant('robots', claimed_time='now')

        # manually follow redirects from /robots -> /~robots/
        response = self.client.GxT("/robots")
        assert response.code == 302
        assert response.headers['Location'] == '/robots/'
        response = self.client.GxT("/robots/")
        assert response.code == 302
        assert response.headers['Location'] == '/~robots/'
        response = self.client.GET("/~robots/")
        assert response.code == 200
        assert '<h1>~robots</h1>' in response.body

        # /robots.txt
        response = self.client.GET("/robots.txt")
        assert response.code == 200
        assert response.body == 'User-agent: *\nDisallow: /*.json\nDisallow: /on/*\n'

    def test_unavailable(self):
        self.make_participant("bob")
        code, body = self.change_username("bob")
        assert code == 400
        assert body['error_message_long'] == "The username 'bob' is already taken."

    def test_too_long(self):
        username = "I am way too long, and you know it, and the American people know it."
        code, body = self.change_username(username)
        assert code == 400
        assert body['error_message_long'] == "The username '%s' is too long." % username
