# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import datetime

import pytest
from aspen.utils import utcnow

from gratipay.exceptions import NotSane
from gratipay.models.account_elsewhere import AccountElsewhere
from gratipay.models.participant import (
    NeedConfirmation, Participant, TeamCantBeOnlyAuth, WontTakeOverWithIdentities
)
from gratipay.testing import Harness, D,P


class TestAbsorptions(Harness):
    # TODO: These tests should probably be moved to absorptions tests
    def setUp(self):
        Harness.setUp(self)
        now = utcnow()
        hour_ago = now - datetime.timedelta(hours=1)
        for i, username in enumerate(['alice', 'bob', 'carl']):
            p = self.make_participant( username
                                     , claimed_time=hour_ago
                                     , last_bill_result=''
                                     , balance=D(i)
                                      )
            setattr(self, username, p)

        deadbeef = self.make_participant('deadbeef', balance=D('18.03'), elsewhere='twitter')
        self.expected_new_balance = self.bob.balance + deadbeef.balance
        deadbeef_twitter = AccountElsewhere.from_user_name('twitter', 'deadbeef')

        self.make_tip(self.carl, self.bob, '1.00')
        self.make_tip(self.alice, deadbeef, '1.00')
        self.bob.take_over(deadbeef_twitter, have_confirmation=True)
        self.deadbeef_archived = Participant.from_id(deadbeef.id)

    def test_participant_can_be_instantiated(self):
        expected = Participant
        actual = P('alice').__class__
        assert actual is expected

    @pytest.mark.xfail(reason="#3399")
    def test_bob_has_two_dollars_in_tips(self):
        expected = D('2.00')
        actual = self.bob.receiving
        assert actual == expected

    def test_alice_gives_to_bob_now(self):
        assert self.get_tip('alice', 'bob') == D('1.00')

    def test_deadbeef_is_archived(self):
        actual = self.db.one( "SELECT count(*) FROM absorptions "
                              "WHERE absorbed_by='bob' AND absorbed_was='deadbeef'"
                             )
        expected = 1
        assert actual == expected

    def test_alice_doesnt_gives_to_deadbeef_anymore(self):
        assert self.get_tip('alice', 'deadbeef') == D('0.00')

    def test_alice_doesnt_give_to_whatever_deadbeef_was_archived_as_either(self):
        assert self.get_tip('alice', self.deadbeef_archived.username) == D('0.00')

    def test_there_is_no_more_deadbeef(self):
        actual = P('deadbeef')
        assert actual is None

    def test_balance_was_transferred(self):
        fresh_bob = P('bob')
        assert fresh_bob.balance == self.bob.balance == self.expected_new_balance
        assert self.deadbeef_archived.balance == 0


class TestTakeOver(Harness):

    def test_cross_tip_doesnt_become_self_tip(self):
        alice_twitter = self.make_elsewhere('twitter', 1, 'alice')
        bob_twitter   = self.make_elsewhere('twitter', 2, 'bob')
        alice = alice_twitter.opt_in('alice')[0].participant
        bob = bob_twitter.opt_in('bob')[0].participant
        self.make_tip(alice, bob, '1.00')
        bob.take_over(alice_twitter, have_confirmation=True)
        self.db.self_check()

    def test_zero_cross_tip_doesnt_become_self_tip(self):
        alice_twitter = self.make_elsewhere('twitter', 1, 'alice')
        bob_twitter   = self.make_elsewhere('twitter', 2, 'bob')
        alice = alice_twitter.opt_in('alice')[0].participant
        bob = bob_twitter.opt_in('bob')[0].participant
        self.make_tip(alice, bob, '1.00')
        self.make_tip(alice, bob, '0.00')

        bob.take_over(alice_twitter, have_confirmation=True)
        self.db.self_check()

    def test_do_not_take_over_zero_tips_giving(self):
        alice_twitter = self.make_elsewhere('twitter', 1, 'alice')
        bob = self.make_elsewhere('twitter', 2, 'bob').opt_in('bob')[0].participant
        carl_twitter  = self.make_elsewhere('twitter', 3, 'carl')
        alice = alice_twitter.opt_in('alice')[0].participant
        carl = carl_twitter.opt_in('carl')[0].participant
        self.make_tip(carl, bob, '1.00')
        self.make_tip(carl, bob, '0.00')
        alice.take_over(carl_twitter, have_confirmation=True)
        ntips = self.db.one("select count(*) from tips")
        assert 2 == ntips
        self.db.self_check()

    def test_do_not_take_over_zero_tips_receiving(self):
        alice_twitter = self.make_elsewhere('twitter', 1, 'alice')
        bob_twitter   = self.make_elsewhere('twitter', 2, 'bob')
        carl_twitter  = self.make_elsewhere('twitter', 3, 'carl')
        alice = alice_twitter.opt_in('alice')[0].participant
        bob = bob_twitter.opt_in('bob')[0].participant
        carl = carl_twitter.opt_in('carl')[0].participant
        self.make_tip(bob, carl, '1.00')
        self.make_tip(bob, carl, '0.00')
        alice.take_over(carl_twitter, have_confirmation=True)
        ntips = self.db.one("select count(*) from tips")
        assert 2 == ntips
        self.db.self_check()

    def test_is_funded_is_correct_for_consolidated_tips_receiving(self):
        alice = self.make_participant('alice', claimed_time='now', balance=1)
        bob = self.make_participant('bob', elsewhere='twitter')
        carl = self.make_participant('carl', elsewhere='github')
        self.make_tip(alice, bob, '1.00')  # funded
        self.make_tip(alice, carl, '5.00')  # not funded
        bob.take_over(('github', str(carl.id)), have_confirmation=True)
        tips = self.db.all("select * from tips where amount > 0 order by id asc")
        assert len(tips) == 3
        assert tips[-1].amount == 6
        assert tips[-1].is_funded is False
        self.db.self_check()

    def test_take_over_fails_if_it_would_result_in_just_a_team_account(self):
        alice_github = self.make_elsewhere('github', 2, 'alice')
        alice = alice_github.opt_in('alice')[0].participant

        a_team_github = self.make_elsewhere('github', 1, 'a_team', is_team=True)
        a_team_github.opt_in('a_team')

        pytest.raises( TeamCantBeOnlyAuth
                     , alice.take_over
                     , a_team_github
                     , have_confirmation=True
                      )

    def test_take_over_is_fine_with_identity_info_on_primary(self):
        TT = self.db.one("SELECT id FROM countries WHERE code='TT'")
        alice = self.make_participant('alice')
        alice.add_email('alice@example.com')
        alice.verify_email('alice@example.com', alice.get_email('alice@example.com').nonce)
        alice.store_identity_info(TT, 'nothing-enforced', {})

        bob_github = self.make_elsewhere('github', 2, 'bob')
        bob_github.opt_in('bob')

        alice.take_over(bob_github, have_confirmation=True)
        self.db.self_check()

    def test_take_over_fails_if_secondary_has_identity_info(self):
        TT = self.db.one("SELECT id FROM countries WHERE code='TT'")
        alice = self.make_participant('alice')

        bob_github = self.make_elsewhere('github', 2, 'bob')
        bob = bob_github.opt_in('bob')[0].participant
        bob.add_email('bob@example.com')
        bob.verify_email('bob@example.com', bob.get_email('bob@example.com').nonce)
        bob.store_identity_info(TT, 'nothing-enforced', {})

        pytest.raises(WontTakeOverWithIdentities, alice.take_over, bob_github)

    def test_idempotent(self):
        alice_twitter = self.make_elsewhere('twitter', 1, 'alice')
        bob_github    = self.make_elsewhere('github', 2, 'bob')
        alice = alice_twitter.opt_in('alice')[0].participant
        alice.take_over(bob_github, have_confirmation=True)
        alice.take_over(bob_github, have_confirmation=True)
        self.db.self_check()

    def test_email_addresses_merging(self):
        alice = self.make_participant('alice')
        alice.add_email('alice@example.com')
        alice.add_email('alice@example.net')
        alice.add_email('alice@example.org')
        alice.verify_email('alice@example.org', alice.get_email('alice@example.org').nonce)
        bob_github = self.make_elsewhere('github', 2, 'bob')
        bob = bob_github.opt_in('bob')[0].participant
        bob.add_email('alice@example.com')
        bob.verify_email('alice@example.com', bob.get_email('alice@example.com').nonce)
        bob.add_email('alice@example.net')
        bob.add_email('bob@example.net')
        alice.take_over(bob_github, have_confirmation=True)

        alice_emails = {e.address: e for e in alice.get_emails()}
        assert len(alice_emails) == 4
        assert alice_emails['alice@example.com'].verified
        assert alice_emails['alice@example.org'].verified
        assert not alice_emails['alice@example.net'].verified
        assert not alice_emails['bob@example.net'].verified

        assert not Participant.from_id(bob.id).get_emails()


    # The below tests were moved up here from TestParticipant, and may be duplicates.

    def hackedSetUp(self):
        for username in ['alice', 'bob', 'carl']:
            p = self.make_participant(username, claimed_time='now', elsewhere='twitter')
            setattr(self, username, p)

    def test_connecting_unknown_account_fails(self):
        self.hackedSetUp()
        with self.assertRaises(NotSane):
            self.bob.take_over(('github', 'jim'))

    def test_cant_take_over_claimed_participant_without_confirmation(self):
        self.hackedSetUp()
        with self.assertRaises(NeedConfirmation):
            self.alice.take_over(('twitter', str(self.bob.id)))

    def test_taking_over_yourself_sets_all_to_zero(self):
        self.hackedSetUp()
        self.make_tip(self.alice, self.bob, '1.00')
        self.alice.take_over(('twitter', str(self.bob.id)), have_confirmation=True)
        expected = D('0.00')
        actual = self.alice.giving
        assert actual == expected

    def test_alice_ends_up_tipping_bob_two_dollars(self):
        self.hackedSetUp()
        self.make_tip(self.alice, self.bob, '1.00')
        self.make_tip(self.alice, self.carl, '1.00')
        self.bob.take_over(('twitter', str(self.carl.id)), have_confirmation=True)
        assert self.get_tip('alice', 'bob') == D('2.00')

    def test_bob_ends_up_tipping_alice_two_dollars(self):
        self.hackedSetUp()
        self.make_tip(self.bob, self.alice, '1.00')
        self.make_tip(self.carl, self.alice, '1.00')
        self.bob.take_over(('twitter', str(self.carl.id)), have_confirmation=True)
        assert self.get_tip('bob', 'alice') == D('2.00')

    def test_ctime_comes_from_the_older_tip(self):
        self.hackedSetUp()
        self.make_tip(self.alice, self.bob, '1.00')
        self.make_tip(self.alice, self.carl, '1.00')
        self.bob.take_over(('twitter', str(self.carl.id)), have_confirmation=True)

        ctimes = self.db.all("""
            SELECT ctime
              FROM tips
             WHERE tipper = 'alice'
               AND tippee = 'bob'
        """)
        assert len(ctimes) == 2
        assert ctimes[0] == ctimes[1]
