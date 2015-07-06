from __future__ import absolute_import, division, print_function, unicode_literals

from datetime import date
from decimal import Decimal as D

import mock
import pytest

from gratipay.billing.payday import Payday
from gratipay.models.community import Community
from gratipay.models.participant import Participant
from gratipay.testing import Harness


class TestClosing(Harness):

    # close

    def test_close_closes(self):
        alice = self.make_participant('alice', claimed_time='now')
        alice.close()
        assert Participant.from_username('alice').is_closed

    def test_close_fails_if_still_a_balance(self):
        alice = self.make_participant('alice', claimed_time='now', balance=D('10.00'))
        with pytest.raises(alice.BalanceIsNotZero):
            alice.close()

    def test_close_page_is_usually_available(self):
        self.make_participant('alice', claimed_time='now')
        body = self.client.GET('/~alice/settings/close', auth_as='alice').body
        assert 'Personal Information' in body

    def test_close_page_is_not_available_during_payday(self):
        Payday.start()
        self.make_participant('alice', claimed_time='now')
        body = self.client.GET('/~alice/settings/close', auth_as='alice').body
        assert 'Personal Information' not in body
        assert 'Try Again Later' in body

    def test_can_post_to_close_page(self):
        self.make_participant('alice', claimed_time='now')
        response = self.client.PxST('/~alice/settings/close', auth_as='alice')
        assert response.code == 302
        assert response.headers['Location'] == '/~alice/'
        assert Participant.from_username('alice').is_closed

    def test_cant_post_to_close_page_during_payday(self):
        Payday.start()
        self.make_participant('alice', claimed_time='now')
        body = self.client.POST('/~alice/settings/close', auth_as='alice').body
        assert 'Try Again Later' in body


    # ctg - clear_tips_giving

    def test_ctg_clears_tips_giving(self):
        alice = self.make_participant('alice', claimed_time='now', last_bill_result='')
        alice.set_tip_to(self.make_participant('bob', claimed_time='now').username, D('1.00'))
        ntips = lambda: self.db.one("SELECT count(*) FROM current_tips "
                                    "WHERE tipper='alice' AND amount > 0")
        assert ntips() == 1
        with self.db.get_cursor() as cursor:
            alice.clear_tips_giving(cursor)
        assert ntips() == 0

    def test_ctg_doesnt_duplicate_zero_tips(self):
        alice = self.make_participant('alice', claimed_time='now')
        bob = self.make_participant('bob')
        alice.set_tip_to(bob, D('1.00'))
        alice.set_tip_to(bob, D('0.00'))
        ntips = lambda: self.db.one("SELECT count(*) FROM tips WHERE tipper='alice'")
        assert ntips() == 2
        with self.db.get_cursor() as cursor:
            alice.clear_tips_giving(cursor)
        assert ntips() == 2

    def test_ctg_doesnt_zero_when_theres_no_tip(self):
        alice = self.make_participant('alice')
        ntips = lambda: self.db.one("SELECT count(*) FROM tips WHERE tipper='alice'")
        assert ntips() == 0
        with self.db.get_cursor() as cursor:
            alice.clear_tips_giving(cursor)
        assert ntips() == 0

    def test_ctg_clears_multiple_tips_giving(self):
        alice = self.make_participant('alice', claimed_time='now')
        alice.set_tip_to(self.make_participant('bob', claimed_time='now').username, D('1.00'))
        alice.set_tip_to(self.make_participant('carl', claimed_time='now').username, D('1.00'))
        alice.set_tip_to(self.make_participant('darcy', claimed_time='now').username, D('1.00'))
        alice.set_tip_to(self.make_participant('evelyn', claimed_time='now').username, D('1.00'))
        alice.set_tip_to(self.make_participant('francis', claimed_time='now').username, D('1.00'))
        ntips = lambda: self.db.one("SELECT count(*) FROM current_tips "
                                    "WHERE tipper='alice' AND amount > 0")
        assert ntips() == 5
        with self.db.get_cursor() as cursor:
            alice.clear_tips_giving(cursor)
        assert ntips() == 0


    # ctr - clear_tips_receiving

    def test_ctr_clears_tips_receiving(self):
        alice = self.make_participant('alice')
        self.make_participant('bob', claimed_time='now').set_tip_to(alice, D('1.00'))
        ntips = lambda: self.db.one("SELECT count(*) FROM current_tips "
                                    "WHERE tippee='alice' AND amount > 0")
        assert ntips() == 1
        with self.db.get_cursor() as cursor:
            alice.clear_tips_receiving(cursor)
        assert ntips() == 0

    def test_ctr_doesnt_duplicate_zero_tips(self):
        alice = self.make_participant('alice')
        bob = self.make_participant('bob', claimed_time='now')
        bob.set_tip_to(alice, D('1.00'))
        bob.set_tip_to(alice, D('0.00'))
        ntips = lambda: self.db.one("SELECT count(*) FROM tips WHERE tippee='alice'")
        assert ntips() == 2
        with self.db.get_cursor() as cursor:
            alice.clear_tips_receiving(cursor)
        assert ntips() == 2

    def test_ctr_doesnt_zero_when_theres_no_tip(self):
        alice = self.make_participant('alice')
        ntips = lambda: self.db.one("SELECT count(*) FROM tips WHERE tippee='alice'")
        assert ntips() == 0
        with self.db.get_cursor() as cursor:
            alice.clear_tips_receiving(cursor)
        assert ntips() == 0

    def test_ctr_clears_multiple_tips_receiving(self):
        alice = self.make_participant('alice')
        self.make_participant('bob', claimed_time='now').set_tip_to(alice, D('1.00'))
        self.make_participant('carl', claimed_time='now').set_tip_to(alice, D('2.00'))
        self.make_participant('darcy', claimed_time='now').set_tip_to(alice, D('3.00'))
        self.make_participant('evelyn', claimed_time='now').set_tip_to(alice, D('4.00'))
        self.make_participant('francis', claimed_time='now').set_tip_to(alice, D('5.00'))
        ntips = lambda: self.db.one("SELECT count(*) FROM current_tips "
                                    "WHERE tippee='alice' AND amount > 0")
        assert ntips() == 5
        with self.db.get_cursor() as cursor:
            alice.clear_tips_receiving(cursor)
        assert ntips() == 0


    # cpi - clear_personal_information

    @mock.patch.object(Participant, '_mailer')
    def test_cpi_clears_personal_information(self, mailer):
        alice = self.make_participant( 'alice'
                                     , anonymous_giving=True
                                     , anonymous_receiving=True
                                     , avatar_url='img-url'
                                     , email_address='alice@example.com'
                                     , claimed_time='now'
                                     , session_token='deadbeef'
                                     , session_expires='2000-01-01'
                                     , giving=20
                                     , receiving=40
                                     , npatrons=21
                                      )
        alice.upsert_statement('en', 'not forgetting to be awesome!')
        alice.add_email('alice@example.net')

        with self.db.get_cursor() as cursor:
            alice.clear_personal_information(cursor)
        new_alice = Participant.from_username('alice')

        assert alice.get_statement(['en']) == (None, None)
        assert alice.anonymous_giving == new_alice.anonymous_giving == False
        assert alice.anonymous_receiving == new_alice.anonymous_receiving == False
        assert alice.number == new_alice.number == 'singular'
        assert alice.avatar_url == new_alice.avatar_url == None
        assert alice.email_address == new_alice.email_address == None
        assert alice.claimed_time == new_alice.claimed_time == None
        assert alice.giving == new_alice.giving == 0
        assert alice.receiving == new_alice.receiving == 0
        assert alice.npatrons == new_alice.npatrons == 0
        assert alice.session_token == new_alice.session_token == None
        assert alice.session_expires.year == new_alice.session_expires.year == date.today().year
        assert not alice.get_emails()

        team = self.make_participant('team', number='plural')
        with self.db.get_cursor() as cursor:
            team.clear_personal_information(cursor)
        team2 = Participant.from_username('team')
        assert team.number == team2.number == 'singular'

    def test_cpi_clears_communities(self):
        alice = self.make_participant('alice')
        alice.insert_into_communities(True, 'test', 'test')
        bob = self.make_participant('bob')
        bob.insert_into_communities(True, 'test', 'test')

        assert Community.from_slug('test').nmembers == 2  # sanity check

        with self.db.get_cursor() as cursor:
            alice.clear_personal_information(cursor)

        assert Community.from_slug('test').nmembers == 1


    # uic = update_is_closed

    def test_uic_updates_is_closed(self):
        alice = self.make_participant('alice')
        alice.update_is_closed(True)

        assert alice.is_closed
        assert Participant.from_username('alice').is_closed

    def test_uic_updates_is_closed_False(self):
        alice = self.make_participant('alice')
        alice.update_is_closed(True)
        alice.update_is_closed(False)

        assert not alice.is_closed
        assert not Participant.from_username('alice').is_closed

    def test_uic_uses_supplied_cursor(self):
        alice = self.make_participant('alice')

        with self.db.get_cursor() as cursor:
            alice.update_is_closed(True, cursor)
            assert alice.is_closed
            assert not Participant.from_username('alice').is_closed
        assert Participant.from_username('alice').is_closed
