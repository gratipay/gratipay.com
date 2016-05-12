from __future__ import absolute_import, division, print_function, unicode_literals

from decimal import Decimal as D
import os

import braintree
import mock
import pytest

from gratipay.billing.exchanges import create_card_hold, MINIMUM_CHARGE
from gratipay.billing.payday import NoPayday, Payday
from gratipay.exceptions import NegativeBalance
from gratipay.models.participant import Participant
from gratipay.testing import Foobar
from gratipay.testing.billing import BillingHarness
from gratipay.testing.emails import EmailHarness


class TestPayday(BillingHarness):
    @mock.patch.object(Payday, 'fetch_card_holds')
    def test_payday_moves_money_above_min_charge(self, fch):
        Enterprise = self.make_team(is_approved=True)
        self.obama.set_payment_instruction(Enterprise, MINIMUM_CHARGE)  # must be >= MINIMUM_CHARGE

        fch.return_value = {}
        Payday.start().run()

        obama = Participant.from_username('obama')
        picard = Participant.from_username('picard')

        assert picard.balance == D(MINIMUM_CHARGE)
        assert obama.balance == D('0.00')
        assert obama.get_due('TheEnterprise') == D('0.00')

    @mock.patch.object(Payday, 'fetch_card_holds')
    def test_payday_moves_money_cumulative_above_min_charge(self, fch):
        Enterprise = self.make_team(is_approved=True)
        self.obama.set_payment_instruction(Enterprise, '5.00')  # < MINIMUM_CHARGE
        # simulate already due amount
        self.db.run("""

            UPDATE payment_instructions ppi
               SET due = '5.00'
             WHERE ppi.participant = 'obama'
               AND ppi.team = 'TheEnterprise'

        """)

        assert self.obama.get_due('TheEnterprise') == D('5.00')

        fch.return_value = {}
        Payday.start().run()

        obama = Participant.from_username('obama')
        picard = Participant.from_username('picard')

        assert picard.balance == D('10.00')
        assert obama.balance == D('0.00')
        assert obama.get_due('TheEnterprise') == D('0.00')

    @mock.patch.object(Payday, 'fetch_card_holds')
    def test_payday_preserves_due_until_charged(self, fch):
        Enterprise = self.make_team(is_approved=True)
        self.obama.set_payment_instruction(Enterprise, '2.00')  # < MINIMUM_CHARGE

        fch.return_value = {}
        Payday.start().run()    # payday 0

        assert self.obama.get_due('TheEnterprise') == D('2.00')

        self.obama.set_payment_instruction(Enterprise, '3.00')  # < MINIMUM_CHARGE
        self.obama.set_payment_instruction(Enterprise, '2.50')  # cumulatively still < MINIMUM_CHARGE

        fch.return_value = {}
        Payday.start().run()    # payday 1

        assert self.obama.get_due('TheEnterprise') == D('4.50')

        fch.return_value = {}
        Payday.start().run()    # payday 2

        assert self.obama.get_due('TheEnterprise') == D('7.00')

        self.obama.set_payment_instruction(Enterprise, '1.00')  # cumulatively still < MINIMUM_CHARGE

        fch.return_value = {}
        Payday.start().run()    # payday 3

        assert self.obama.get_due('TheEnterprise') == D('8.00')

        self.obama.set_payment_instruction(Enterprise, '4.00')  # cumulatively > MINIMUM_CHARGE

        fch.return_value = {}
        Payday.start().run()    # payday 4

        obama = Participant.from_username('obama')
        picard = Participant.from_username('picard')

        assert picard.balance == D('12.00')
        assert obama.balance == D('0.00')
        assert obama.get_due('TheEnterprise') == D('0.00')

    @mock.patch.object(Payday, 'fetch_card_holds')
    def test_payday_only_adds_to_dues_if_valid_cc_exists(self, fch):
        Enterprise = self.make_team(is_approved=True)
        self.obama.set_payment_instruction(Enterprise, '4.00')
        assert self.obama.get_due('TheEnterprise') == D('0.00')

        fch.return_value = {}
        Payday.start().run()    # payday 0

        assert self.obama.get_due('TheEnterprise') == D('4.00')

        fch.return_value = {}
        self.obama_route.update_error("failed") # card fails
        Payday.start().run()    # payday 1

        assert self.obama.get_due('TheEnterprise') == D('4.00')

        fch.return_value = {}
        Payday.start().run()    # payday 2

        assert self.obama.get_due('TheEnterprise') == D('4.00')

    @mock.patch.object(Payday, 'fetch_card_holds')
    def test_payday_does_not_move_money_below_min_charge(self, fch):
        Enterprise  = self.make_team(is_approved=True)
        self.obama.set_payment_instruction(Enterprise, '6.00')  # not enough to reach MINIMUM_CHARGE
        fch.return_value = {}
        Payday.start().run()

        obama = Participant.from_username('obama')
        picard = Participant.from_username('picard')

        assert picard.balance == D('0.00')
        assert obama.balance == D('0.00')
        assert obama.get_due('TheEnterprise') == D('6.00')


    @mock.patch.object(Payday, 'fetch_card_holds')
    def test_payday_doesnt_move_money_from_a_suspicious_account(self, fch):
        self.db.run("""
            UPDATE participants
               SET is_suspicious = true
             WHERE username = 'obama'
        """)
        team = self.make_team(owner=self.homer, is_approved=True)
        self.obama.set_payment_instruction(team, MINIMUM_CHARGE)  # >= MINIMUM_CHARGE!
        fch.return_value = {}
        Payday.start().run()

        obama = Participant.from_username('obama')
        homer = Participant.from_username('homer')

        assert obama.balance == D('0.00')
        assert homer.balance == D('0.00')

    @mock.patch.object(Payday, 'fetch_card_holds')
    def test_payday_doesnt_move_money_to_a_suspicious_account(self, fch):
        self.db.run("""
            UPDATE participants
               SET is_suspicious = true
             WHERE username = 'homer'
        """)
        team = self.make_team(owner=self.homer, is_approved=True)
        self.obama.set_payment_instruction(team, MINIMUM_CHARGE)  # >= MINIMUM_CHARGE!
        fch.return_value = {}
        Payday.start().run()

        obama = Participant.from_username('obama')
        homer = Participant.from_username('homer')

        assert obama.balance == D('0.00')
        assert homer.balance == D('0.00')

    @mock.patch.object(Payday, 'fetch_card_holds')
    def test_nusers_includes_dues(self, fch):
        Enterprise  = self.make_team(is_approved=True)
        self.obama.set_payment_instruction(Enterprise, '6.00')  # below MINIMUM_CHARGE
        fch.return_value = {}
        Payday.start().run()

        assert self.obama.get_due(Enterprise) == D('6.00')

        nusers = self.db.one("SELECT nusers FROM paydays")
        assert nusers == 1

    @mock.patch('gratipay.billing.payday.log')
    def test_start_prepare(self, log):
        self.clear_tables()
        self.make_participant('bob', balance=10, claimed_time=None)
        self.make_participant('carl', balance=10, claimed_time='now')

        payday = Payday.start()

        get_participants = lambda c: c.all("SELECT * FROM payday_participants")

        with self.db.get_cursor() as cursor:
            payday.prepare(cursor)
            participants = get_participants(cursor)

        expected_logging_call_args = [
            ('Starting a new payday.'),
            ('Payday started at {}.'.format(payday.ts_start)),
            ('Prepared the DB.'),
        ]
        expected_logging_call_args.reverse()
        for args, _ in log.call_args_list:
            assert args[0] == expected_logging_call_args.pop()

        log.reset_mock()

        # run a second time, we should see it pick up the existing payday
        second_payday = Payday.start()
        with self.db.get_cursor() as cursor:
            payday.prepare(cursor)
            second_participants = get_participants(cursor)

        assert payday.ts_start == second_payday.ts_start
        participants = list(participants)
        second_participants = list(second_participants)

        # carl is the only valid participant as he has a claimed time
        assert len(participants) == 1
        assert participants == second_participants

        expected_logging_call_args = [
            ('Picking up with an existing payday.'),
            ('Payday started at {}.'.format(second_payday.ts_start)),
            ('Prepared the DB.'),
        ]
        expected_logging_call_args.reverse()
        for args, _ in log.call_args_list:
            assert args[0] == expected_logging_call_args.pop()

    def test_end(self):
        Payday.start().end()
        result = self.db.one("SELECT count(*) FROM paydays "
                             "WHERE ts_end > '1970-01-01'")
        assert result == 1

    def test_end_raises_NoPayday(self):
        with self.assertRaises(NoPayday):
            Payday().end()

    @mock.patch('gratipay.billing.payday.log')
    @mock.patch('gratipay.billing.payday.Payday.payin')
    def test_payday(self, payin, log):
        greeting = 'Greetings, program! It\'s PAYDAY!!!!'
        Payday.start().run()
        log.assert_any_call(greeting)
        assert payin.call_count == 1


class TestPayin(BillingHarness):

    def create_card_holds(self):
        payday = Payday.start()
        with self.db.get_cursor() as cursor:
            payday.prepare(cursor)
            return payday.create_card_holds(cursor)

    @mock.patch.object(Payday, 'fetch_card_holds')
    @mock.patch('braintree.Transaction.submit_for_settlement')
    @mock.patch('braintree.Transaction.sale')
    def test_payin_pays_in(self, sale, sfs, fch):
        fch.return_value = {}
        team = self.make_team('Gratiteam', is_approved=True)
        self.obama.set_payment_instruction(team, MINIMUM_CHARGE)        # >= MINIMUM_CHARGE

        txn_attrs = {
            'amount': MINIMUM_CHARGE,
            'tax_amount': 0,
            'status': 'authorized',
            'custom_fields': {'participant_id': self.obama.id},
            'credit_card': {'token': self.obama_route.address},
            'id': 'dummy_id'
        }
        submitted_txn_attrs = txn_attrs.copy()
        submitted_txn_attrs.update(status='submitted_for_settlement')
        authorized_txn = braintree.Transaction(None, txn_attrs)
        submitted_txn = braintree.Transaction(None, submitted_txn_attrs)
        sale.return_value.transaction = authorized_txn
        sale.return_value.is_success = True
        sfs.return_value.transaction = submitted_txn
        sfs.return_value.is_success = True

        Payday.start().payin()
        payments = self.db.all("SELECT amount, direction FROM payments")
        assert payments == [(MINIMUM_CHARGE, 'to-team'), (MINIMUM_CHARGE, 'to-participant')]

    @mock.patch('braintree.Transaction.sale')
    def test_payin_doesnt_try_failed_cards(self, sale):
        team = self.make_team('Gratiteam', is_approved=True)
        self.obama_route.update_error('error')
        self.obama.set_payment_instruction(team, 1)

        Payday.start().payin()
        assert not sale.called


    # fetch_card_holds - fch

    def test_fch_returns_an_empty_dict_when_there_are_no_card_holds(self):
        assert Payday.start().fetch_card_holds([]) == {}


    @mock.patch.object(Payday, 'fetch_card_holds')
    @mock.patch('gratipay.billing.payday.create_card_hold')
    def test_hold_amount_includes_negative_balance(self, cch, fch):
        self.db.run("""
            UPDATE participants SET balance = -10 WHERE username='obama'
        """)
        team = self.make_team('The Enterprise', is_approved=True)
        self.obama.set_payment_instruction(team, 25)
        fch.return_value = {}
        cch.return_value = (None, 'some error')
        self.create_card_holds()
        assert cch.call_args[0][-1] == 35

    @mock.patch.object(Payday, 'fetch_card_holds')
    @mock.patch('gratipay.billing.payday.create_card_hold')
    def test_hold_amount_excludes_balance(self, cch, fch):
        self.db.run("""
            UPDATE participants SET balance = 5 WHERE username='obama'
        """)
        team = self.make_team('The Enterprise', is_approved=True)
        self.obama.set_payment_instruction(team, 25)
        fch.return_value = {}
        cch.return_value = (None, 'some error')
        self.create_card_holds()
        assert cch.call_args[0][-1] == 20

    def test_payin_fetches_and_uses_existing_holds(self):
        team = self.make_team(owner=self.homer, is_approved=True)
        self.obama.set_payment_instruction(team, '20.00')
        hold, error = create_card_hold(self.db, self.obama, D(20))
        assert hold is not None
        assert not error
        with mock.patch('gratipay.billing.payday.create_card_hold') as cch:
            cch.return_value = (None, None)
            self.create_card_holds()
            assert not cch.called, cch.call_args_list

    @mock.patch.object(Payday, 'fetch_card_holds')
    def test_payin_cancels_existing_holds_of_insufficient_amounts(self, fch):
        team = self.make_team(owner=self.homer, is_approved=True)
        self.obama.set_payment_instruction(team, '30.00')
        hold, error = create_card_hold(self.db, self.obama, D(10))
        assert not error
        fch.return_value = {self.obama.id: hold}
        with mock.patch('gratipay.billing.payday.create_card_hold') as cch:
            fake_hold = object()
            cch.return_value = (fake_hold, None)
            holds = self.create_card_holds()
            hold = braintree.Transaction.find(hold.id)
            assert len(holds) == 1
            assert holds[self.obama.id] is fake_hold
            assert hold.status == 'voided'

    @pytest.mark.xfail(reason="turned this off during Gratipocalypse; turn back on!")
    @mock.patch('gratipay.billing.payday.log')
    def test_payin_cancels_uncaptured_holds(self, log):
        self.janet.set_tip_to(self.homer, 42)
        alice = self.make_participant('alice', claimed_time='now',
                                      is_suspicious=False)
        self.make_exchange('balanced-cc', 50, 0, alice)
        alice.set_tip_to(self.janet, 50)
        Payday.start().payin()
        assert log.call_args_list[-3][0] == ("Captured 0 card holds.",)
        assert log.call_args_list[-2][0] == ("Canceled 1 card holds.",)
        assert Participant.from_id(alice.id).balance == 0
        assert Participant.from_id(self.janet.id).balance == 8
        assert Participant.from_id(self.homer.id).balance == 42

    def test_payin_cant_make_balances_more_negative(self):
        self.db.run("""
            UPDATE participants SET balance = -10 WHERE username='janet'
        """)
        payday = Payday.start()
        with self.db.get_cursor() as cursor:
            payday.prepare(cursor)
            cursor.run("""
                UPDATE payday_participants
                   SET new_balance = -50
                 WHERE username IN ('janet', 'homer')
            """)
            with self.assertRaises(NegativeBalance):
                payday.update_balances(cursor)

    def test_payin_doesnt_make_null_payments(self):
        team = self.make_team('Gratiteam', is_approved=True)
        alice = self.make_participant('alice', claimed_time='now')
        alice.set_payment_instruction(team, 1)
        alice.set_payment_instruction(team, 0)
        Payday.start().payin()
        payments = self.db.all("SELECT * FROM payments WHERE amount = 0")
        assert not payments

    def test_process_payment_instructions(self):
        alice = self.make_participant('alice', claimed_time='now', balance=1)
        picard = self.make_participant('picard', claimed_time='now', last_paypal_result='')
        shelby = self.make_participant('shelby', claimed_time='now', last_paypal_result='')
        Enterprise = self.make_team('The Enterprise', picard, is_approved=True)
        Trident = self.make_team('The Trident', shelby, is_approved=True)
        alice.set_payment_instruction(Enterprise, D('0.51'))
        alice.set_payment_instruction(Trident, D('0.50'))

        payday = Payday.start()
        with self.db.get_cursor() as cursor:
            payday.prepare(cursor)
            payday.process_payment_instructions(cursor)
            assert cursor.one("select balance from payday_teams where slug='TheEnterprise'") == D('0.51')
            assert cursor.one("select balance from payday_teams where slug='TheTrident'") == 0
            payday.update_balances(cursor)

        assert Participant.from_id(alice.id).balance == D('0.49')
        assert Participant.from_username('picard').balance == 0
        assert Participant.from_username('shelby').balance == 0

        payment = self.db.one("SELECT * FROM payments")
        assert payment.amount == D('0.51')
        assert payment.direction == 'to-team'

    @pytest.mark.xfail(reason="haven't migrated_transfer_takes yet")
    def test_transfer_takes(self):
        a_team = self.make_participant('a_team', claimed_time='now', number='plural', balance=20)
        alice = self.make_participant('alice', claimed_time='now')
        a_team.add_member(alice)
        a_team.add_member(self.make_participant('bob', claimed_time='now'))
        a_team.set_take_for(alice, D('1.00'), alice)

        payday = Payday.start()

        # Test that payday ignores takes set after it started
        a_team.set_take_for(alice, D('2.00'), alice)

        # Run the transfer multiple times to make sure we ignore takes that
        # have already been processed
        for i in range(3):
            with self.db.get_cursor() as cursor:
                payday.prepare(cursor)
                payday.transfer_takes(cursor, payday.ts_start)
                payday.update_balances(cursor)

        participants = self.db.all("SELECT username, balance FROM participants")

        for p in participants:
            if p.username == 'a_team':
                assert p.balance == D('18.99')
            elif p.username == 'alice':
                assert p.balance == D('1.00')
            elif p.username == 'bob':
                assert p.balance == D('0.01')
            else:
                assert p.balance == 0

    def test_process_unclaimed(self):
        alice = self.make_participant('alice', claimed_time='now', balance=1)
        picard = self.make_participant('picard', claimed_time='now', last_paypal_result='')
        Enterprise = self.make_team('The Enterprise', picard, is_approved=True)
        alice.set_payment_instruction(Enterprise, D('0.51'))

        payday = Payday.start()
        with self.db.get_cursor() as cursor:
            payday.prepare(cursor)
            payday.process_payment_instructions(cursor)
            payday.process_unclaimed(cursor)
            payday.process_takes(cursor, payday.ts_start)
            assert cursor.one("select new_balance from payday_participants "
                              "where username='picard'") == D('0.51')
            assert cursor.one("select balance from payday_teams where slug='TheEnterprise'") == 0
            payday.update_balances(cursor)

        assert Participant.from_id(alice.id).balance == D('0.49')
        assert Participant.from_username('picard').balance == D('0.51')

        payment = self.db.one("SELECT * FROM payments WHERE direction='to-participant'")
        assert payment.amount == D('0.51')

    def test_take_over_during_payin(self):
        alice = self.make_participant('alice', claimed_time='now', balance=50)
        enterprise = self.make_team('The Enterprise', is_approved=True)
        picard = Participant.from_username(enterprise.owner)
        self.make_participant('bob', claimed_time='now', elsewhere='twitter')
        alice.set_payment_instruction(enterprise, 18)
        payday = Payday.start()
        with self.db.get_cursor() as cursor:
            payday.prepare(cursor)

            # bruce takes over picard
            bruce = self.make_participant('bruce', claimed_time='now')
            bruce.take_over(('twitter', str(picard.id)), have_confirmation=True)
            payday.process_payment_instructions(cursor)

            # billy takes over bruce
            bruce.delete_elsewhere('twitter', str(picard.id))
            billy = self.make_participant('billy', claimed_time='now')
            billy.take_over(('github', str(bruce.id)), have_confirmation=True)

            payday.update_balances(cursor)
        payday.take_over_balances()

        # billy ends up with the money
        assert Participant.from_id(picard.id).balance == 0
        assert Participant.from_id(bruce.id).balance == 0
        assert Participant.from_id(billy.id).balance == 18

    @mock.patch.object(Payday, 'fetch_card_holds')
    @mock.patch('gratipay.billing.payday.capture_card_hold')
    def test_payin_dumps_transfers_for_debugging(self, cch, fch):
        team = self.make_team(owner=self.homer, is_approved=True)
        self.obama.set_payment_instruction(team, '10.00')
        fake_hold = mock.MagicMock()
        fake_hold.amount = 1500
        fch.return_value = {self.obama.id: fake_hold}
        cch.side_effect = Foobar
        open_ = mock.MagicMock()
        open_.side_effect = open
        with mock.patch.dict(__builtins__, {'open': open_}):
            with self.assertRaises(Foobar):
                Payday.start().payin()
        filename = open_.call_args_list[-1][0][0]
        assert filename.endswith('_payments.csv')
        os.unlink(filename)


class TestPayout(BillingHarness):

    tearDownClass = None

    def setUp(self):
        self.enterprise = self.make_team('The Enterprise', is_approved=True)
        self.enterprise.set_ntakes(1000)
        self.TT = self.db.one("SELECT id FROM countries WHERE code2='TT'")

        picard = Participant.from_username(self.enterprise.owner)
        self.identify(picard)

    def make_member(self, username, ntakes):
        member = self.make_participant(username, email_address=username+'@x.y', claimed_time='now')
        self.identify(member)
        self.enterprise.set_ntakes_for(member, ntakes)
        return member

    def identify(self, participant):
        participant.store_identity_info(self.TT, 'nothing-enforced', {})
        participant.set_identity_verification(self.TT, True)

    payday = None
    def start_payday(self):
        self.payday = Payday.start()

    def process_distributions(self):
        if not self.payday:
            self.start_payday()
        with self.db.get_cursor() as cursor:
            self.payday.prepare(cursor)
            cursor.run("UPDATE payday_teams SET balance=99")
            self.payday.process_takes(cursor, self.payday.ts_start)
            self.payday.process_draws(cursor)
            self.payday.update_balances(cursor)


    # pd - process_distributions -- This is a pseudo-function, if you will; I'm not
    #                               taking the time to refactor Payday right now.

    def test_pd_processes_takes(self):
        self.make_member('crusher', 500)
        self.make_member('bruiser', 400)
        self.process_distributions()
        assert Participant.from_username('crusher').balance == D('49.50')
        assert Participant.from_username('bruiser').balance == D('39.60')
        assert Participant.from_username('picard').balance  == D(' 9.90')

    def test_pd_ignores_takes_set_after_the_start_of_payday(self):
        self.make_member('crusher', 500)
        self.start_payday()
        self.make_member('bruiser', 400)
        self.process_distributions()
        assert Participant.from_username('crusher').balance == D('49.50')
        assert Participant.from_username('bruiser').balance == D(' 0.00')
        assert Participant.from_username('picard').balance  == D('49.50')

    def test_pd_ignores_takes_that_have_already_been_processed(self):
        self.make_member('crusher', 500)
        self.start_payday()
        self.make_member('bruiser', 400)
        self.process_distributions()
        self.process_distributions()
        self.process_distributions()
        self.process_distributions()
        self.process_distributions()
        assert Participant.from_username('crusher').balance == D('49.50')
        assert Participant.from_username('bruiser').balance == D(' 0.00')
        assert Participant.from_username('picard').balance  == D('49.50')

    def test_pd_is_happy_to_deal_the_owner_in(self):
        self.make_member('crusher', 500)
        self.make_member('bruiser', 400)
        self.enterprise.set_ntakes_for(Participant.from_username(self.enterprise.owner), 50)
        self.process_distributions()
        assert Participant.from_username('crusher').balance == D('49.50')
        assert Participant.from_username('bruiser').balance == D('39.60')
        assert Participant.from_username('picard').balance  == D(' 9.90')

    def test_pd_respects_baseline(self):
        self.db.run("UPDATE teams SET baseline=33")
        self.make_member('crusher', 500)
        self.process_distributions()
        assert Participant.from_username('crusher').balance == D('33.00')
        assert Participant.from_username('picard').balance  == D('66.00')

    def test_pd_leaves_the_rest_for_the_owner(self):
        self.make_member('crusher', 500)
        self.process_distributions()
        assert Participant.from_username('crusher').balance == D('49.50')
        assert Participant.from_username('picard').balance  == D('49.50')

    def test_pd_handles_baseline_and_draw_gracefully(self):
        self.db.run("UPDATE teams SET baseline=33")
        self.make_member('crusher', 500)
        self.process_distributions()
        assert Participant.from_username('crusher').balance == D('33.00')
        assert Participant.from_username('picard').balance  == D('66.00')


class TestNotifyParticipants(EmailHarness):

    def test_it_notifies_participants(self):
        kalel = self.make_participant('kalel', claimed_time='now', is_suspicious=False,
                                      email_address='kalel@example.net', notify_charge=3)
        team = self.make_team('Gratiteam', is_approved=True)
        kalel.set_payment_instruction(team, 10)

        for status in ('failed', 'succeeded'):
            payday = Payday.start()
            self.make_exchange('balanced-cc', 10, 0, kalel, status)
            payday.end()
            payday.notify_participants()

            emails = self.db.one('SELECT * FROM email_queue')
            assert emails.spt_name == 'charge_'+status

            Participant.dequeue_emails()
            assert self.get_last_email()['to'] == 'kalel <kalel@example.net>'
            assert 'Gratiteam' in self.get_last_email()['body_text']
            assert 'Gratiteam' in self.get_last_email()['body_html']
