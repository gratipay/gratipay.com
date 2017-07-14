# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing import Harness
from gratipay.models.participant import Participant


class TestFromEmail(Harness):

    def test_returns_participant_by_primary_email(self):
        alice = self.make_participant('alice')
        self.add_and_verify_email(alice, 'alice@gratipay.com')

        assert Participant.from_email('alice@gratipay.com').username == 'alice'

    def test_returns_participant_by_non_primary_email(self):
        alice = self.make_participant('alice')
        self.add_and_verify_email(alice, 'alice@gratipay.com')
        self.add_and_verify_email(alice, 'alice_non_primary@gratipay.com')

        assert Participant.from_username('alice').email_address == 'alice@gratipay.com'
        assert Participant.from_email('alice_non_primary@gratipay.com').username == 'alice'

    def test_returns_none_for_unverified_email(self):
        alice = self.make_participant('alice')
        alice.start_email_verification('alice@gratipay.com')

        assert Participant.from_email('alice@gratipay.com') is None

    def test_returns_none_if_no_email_exists(self):
        assert Participant.from_email('dummy@gratipay.com') is None
