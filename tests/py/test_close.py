from __future__ import absolute_import, division, print_function, unicode_literals

from datetime import date

import mock
import pytest

from gratipay.models.community import Community
from gratipay.models.participant import Participant
from gratipay.testing import Harness, D,P
from gratipay.testing.billing import PaydayMixin


class TestClose(Harness, PaydayMixin):

    def test_close_closes(self):
        alice = self.make_participant('alice', claimed_time='now')
        alice.close()
        assert P('alice').is_closed

    def test_close_fails_if_still_a_balance(self):
        alice = self.make_participant('alice', claimed_time='now', balance=D('10.00'))
        with pytest.raises(alice.BalanceIsNotZero):
            alice.close()

    def test_close_can_be_overriden_for_balance_though(self):
        alice = self.make_participant('alice', claimed_time='now', balance=D('10.00'))
        alice.close(require_zero_balance=False)
        assert P('alice').is_closed

    def test_close_can_be_overriden_for_negative_balance_too(self):
        alice = self.make_participant('alice', claimed_time='now', balance=D('-10.00'))
        alice.close(require_zero_balance=False)
        assert P('alice').is_closed

    def test_close_fails_if_still_owns_a_team(self):
        alice = self.make_participant('alice', claimed_time='now')
        self.make_team(owner=alice)
        with pytest.raises(alice.StillOnATeam):
            alice.close()

    def test_close_succeeds_if_team_is_closed(self):
        alice = self.make_participant('alice', claimed_time='now')
        self.make_team(owner=alice, is_closed=True)
        alice.close()
        assert P('alice').is_closed


class TestClosePage(Harness, PaydayMixin):

    def test_close_page_is_usually_available(self):
        self.make_participant('alice', claimed_time='now')
        body = self.client.GET('/~alice/settings/close', auth_as='alice').body
        assert 'Personal Information' in body

    def test_close_page_shows_a_message_to_team_owners(self):
        alice = self.make_participant('alice', claimed_time='now')
        self.make_team('A', alice)
        body = self.client.GET('/~alice/settings/close', auth_as='alice').body
        assert 'Please close the following projects first:' in body

    def test_can_post_to_close_page(self):
        self.make_participant('alice', claimed_time='now')
        response = self.client.PxST('/~alice/settings/close', auth_as='alice')
        assert response.code == 302
        assert response.headers['Location'] == '/~alice/'
        assert P('alice').is_closed


    # balance checks

    def test_close_page_is_not_available_to_owner_with_positive_balance(self):
        self.make_participant('alice', claimed_time='now', last_paypal_result='', balance=10)
        body = self.client.GET('/~alice/settings/close', auth_as='alice').body
        assert 'Personal Information' not in body
        assert 'You have a balance' in body

    def test_close_page_is_not_available_to_owner_with_negative_balance(self):
        self.make_participant('alice', claimed_time='now', last_paypal_result='', balance=-10)
        body = self.client.GET('/~alice/settings/close', auth_as='alice').body
        assert 'Personal Information' not in body
        assert 'You have a balance' in body

    def test_sends_owner_with_balance_and_no_paypal_on_quest_for_paypal(self):
        self.make_participant('alice', claimed_time='now', balance=10)
        body = self.client.GET('/~alice/settings/close', auth_as='alice').body
        assert 'Personal Information' not in body
        assert 'You have a balance' not in body
        assert 'link a PayPal account' in body

    def test_but_close_page_is_available_to_admin_even_with_positive_balance(self):
        self.make_participant('admin', claimed_time='now', is_admin=True)
        self.make_participant('alice', claimed_time='now', balance=10)
        body = self.client.GET('/~alice/settings/close', auth_as='admin').body
        assert 'Personal Information' in body
        assert 'Careful!' in body

    def test_and_close_page_is_available_to_admin_even_with_negative_balance(self):
        self.make_participant('admin', claimed_time='now', is_admin=True)
        self.make_participant('alice', claimed_time='now', balance=-10)
        body = self.client.GET('/~alice/settings/close', auth_as='admin').body
        assert 'Personal Information' in body
        assert 'Careful!' in body

    def test_posting_with_balance_fails_for_owner(self):
        self.make_participant('alice', claimed_time='now', balance=10)
        response = self.client.PxST('/~alice/settings/close', auth_as='alice')
        assert response.code == 400
        assert not P('alice').is_closed

    def test_posting_with_balance_succeeds_for_admin(self):
        self.make_participant('admin', claimed_time='now', is_admin=True)
        self.make_participant('alice', claimed_time='now', balance=-10)
        response = self.client.PxST('/~alice/settings/close', auth_as='admin')
        assert response.code == 302
        assert response.headers['Location'] == '/~alice/'
        assert P('alice').is_closed


    # payday check

    def check_under_payday(self, username):
        body = self.client.GET('/~alice/settings/close', auth_as=username).body
        assert 'Personal Information' not in body
        assert 'Try Again Later' in body

    def test_close_page_is_not_available_during_payday(self):
        self.make_participant('alice', claimed_time='now')
        self.start_payday()
        self.check_under_payday('alice')

    def test_even_for_admin(self):
        self.make_participant('admin', claimed_time='now', is_admin=True)
        self.make_participant('alice', claimed_time='now')
        self.start_payday()
        self.check_under_payday('admin')

    def test_cant_post_to_close_page_during_payday(self):
        self.start_payday()
        self.make_participant('alice', claimed_time='now')
        body = self.client.POST('/~alice/settings/close', auth_as='alice').body
        assert 'Try Again Later' in body


class TestClearPaymentInstructions(Harness):

    def test_clears_payment_instructions(self):
        alice = self.make_participant('alice', claimed_time='now', last_bill_result='')
        alice.set_payment_instruction(self.make_team(), D('1.00'))
        npayment_instructions = lambda: self.db.one( "SELECT count(*) "
                                                     "FROM current_payment_instructions "
                                                     "WHERE participant_id=%s AND amount > 0"
                                                   , (alice.id,)
                                                    )
        assert npayment_instructions() == 1
        with self.db.get_cursor() as cursor:
            alice.clear_payment_instructions(cursor)
        assert npayment_instructions() == 0

    def test_doesnt_duplicate_zero_payment_instructions(self):
        alice = self.make_participant('alice', claimed_time='now')
        A = self.make_team()
        alice.set_payment_instruction(A, D('1.00'))
        alice.set_payment_instruction(A, D('0.00'))
        npayment_instructions = lambda: self.db.one("SELECT count(*) FROM payment_instructions "
                                                    "WHERE participant_id=%s", (alice.id,))
        assert npayment_instructions() == 2
        with self.db.get_cursor() as cursor:
            alice.clear_payment_instructions(cursor)
        assert npayment_instructions() == 2

    def test_doesnt_zero_when_theres_no_payment_instruction(self):
        alice = self.make_participant('alice')
        npayment_instructions = lambda: self.db.one("SELECT count(*) FROM payment_instructions "
                                                    "WHERE participant_id=%s", (alice.id,))
        assert npayment_instructions() == 0
        with self.db.get_cursor() as cursor:
            alice.clear_payment_instructions(cursor)
        assert npayment_instructions() == 0

    def test_clears_multiple_payment_instructions(self):
        alice = self.make_participant('alice', claimed_time='now')
        alice.set_payment_instruction(self.make_team('A'), D('1.00'))
        alice.set_payment_instruction(self.make_team('B'), D('1.00'))
        alice.set_payment_instruction(self.make_team('C'), D('1.00'))
        alice.set_payment_instruction(self.make_team('D'), D('1.00'))
        alice.set_payment_instruction(self.make_team('E'), D('1.00'))
        npayment_instructions = lambda: self.db.one( "SELECT count(*) "
                                                     "FROM current_payment_instructions "
                                                     "WHERE participant_id=%s AND amount > 0"
                                                   , (alice.id,)
                                                    )
        assert npayment_instructions() == 5
        with self.db.get_cursor() as cursor:
            alice.clear_payment_instructions(cursor)
        assert npayment_instructions() == 0


class TestClearPersonalInformation(Harness):

    def test_clears_personal_information(self):
        alice = self.make_participant( 'alice'
                                     , anonymous_giving=True
                                     , avatar_url='img-url'
                                     , email_address='alice@example.com'
                                     , claimed_time='now'
                                     , session_token='deadbeef'
                                     , session_expires='2000-01-01'
                                     , giving=20
                                     , taking=40
                                      )
        alice.upsert_statement('en', 'not forgetting to be awesome!')
        alice.add_email('alice@example.net')

        with self.db.get_cursor() as cursor:
            alice.clear_personal_information(cursor)
        new_alice = P('alice')

        assert alice.get_statement(['en']) == (None, None)
        assert alice.anonymous_giving == new_alice.anonymous_giving == False
        assert alice.avatar_url == new_alice.avatar_url == None
        assert alice.email_address == new_alice.email_address == None
        assert alice.claimed_time == new_alice.claimed_time == None
        assert alice.giving == new_alice.giving == 0
        assert alice.taking == new_alice.taking == 0
        assert alice.session_token == new_alice.session_token == None
        assert alice.session_expires.year == new_alice.session_expires.year == date.today().year
        assert not alice.get_emails()

    def test_clears_communities(self):
        alice = self.make_participant('alice')
        alice.insert_into_communities(True, 'test', 'test')
        bob = self.make_participant('bob')
        bob.insert_into_communities(True, 'test', 'test')

        assert Community.from_slug('test').nmembers == 2  # sanity check

        with self.db.get_cursor() as cursor:
            alice.clear_personal_information(cursor)

        assert Community.from_slug('test').nmembers == 1

    def test_clears_personal_identities(self):
        alice = self.make_participant('alice', email_address='alice@example.com')
        US = self.db.one("SELECT id FROM countries WHERE code='US'")
        alice.store_identity_info(US, 'nothing-enforced', {'name': 'Alice'})
        assert len(alice.list_identity_metadata()) == 1
        assert self.db.one('SELECT count(*) FROM participant_identities;') == 1

        with self.db.get_cursor() as cursor:
            alice.clear_personal_information(cursor)

        assert len(alice.list_identity_metadata()) == 0
        assert self.db.one('SELECT count(*) FROM participant_identities;') == 0


class TestUpdateIsClosed(Harness):

    def test_updates_is_closed(self):
        alice = self.make_participant('alice')
        alice.update_is_closed(True)

        assert alice.is_closed
        assert P('alice').is_closed

    def test_updates_is_closed_False(self):
        alice = self.make_participant('alice')
        alice.update_is_closed(True)
        alice.update_is_closed(False)

        assert not alice.is_closed
        assert not P('alice').is_closed

    def test_uses_supplied_cursor(self):
        alice = self.make_participant('alice')

        with self.db.get_cursor() as cursor:
            alice.update_is_closed(True, cursor)
            assert alice.is_closed
            assert not P('alice').is_closed
        assert P('alice').is_closed
