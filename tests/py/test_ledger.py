from __future__ import absolute_import, division, print_function, unicode_literals

from decimal import Decimal as D

from gratipay.testing import Harness
from gratipay.models.participant import Participant
from pytest import raises
from psycopg2 import IntegrityError


class TestJournal(Harness):

    def test_ledger_has_system_accounts(self):
        system_accounts = self.db.all('SELECT type, system FROM accounts')
        assert system_accounts == [ ('asset', 'cash')
                                  , ('asset', 'accounts receivable')
                                  , ('liability', 'accounts payable')
                                  , ('income', 'processing fee revenues')
                                  , ('expense', 'processing fee expenses')
                                  , ('income', 'earned interest')
                                  , ('expense', 'chargeback expenses')
                                   ]

    def test_ledger_creates_accounts_automatically_for_participants(self):
        self.make_participant('alice')
        account = self.db.one("SELECT * FROM accounts WHERE participant IS NOT NULL")
        assert account.participant == 'alice'
        assert account.type == 'liability'

    def test_ledger_creates_accounts_automatically_for_teams(self):
        self.make_team()
        account = self.db.one("SELECT * FROM accounts WHERE team IS NOT NULL")
        assert account.team == 'TheATeam'
        assert account.type == 'liability'

    def test_ledger_is_okay_with_teams_and_participants_with_same_name(self):
        self.make_participant('alice')
        account = self.db.one("SELECT * FROM accounts WHERE participant IS NOT NULL")
        assert account.participant == 'alice'

        self.make_team('alice')
        account = self.db.one("SELECT * FROM accounts WHERE team IS NOT NULL")
        assert account.team == 'alice'

    def test_ledger_catches_system_account_collision(self):
        with raises(IntegrityError):
            self.db.one("INSERT INTO accounts (type, system) VALUES ('asset', 'cash')")

    def test_ledger_catches_participant_account_collision(self):
        self.make_participant('alice')
        with raises(IntegrityError):
            self.db.one("INSERT INTO accounts (type, participant) VALUES ('liability', 'alice')")

    def test_ledger_catches_team_account_collision(self):
        self.make_team()
        with raises(IntegrityError):
            self.db.one("INSERT INTO accounts (type, team) VALUES ('liability', 'TheATeam')")

    def test_ledger_increments_participant_balance(self):
        self.make_team()
        alice = self.make_participant('alice')
        assert alice.balance == 0

        self.db.run("""
            INSERT INTO ledger
                        (amount, debit, credit)
                 VALUES ( 10.77
                        , (SELECT id FROM accounts WHERE team='TheATeam')
                        , (SELECT id FROM accounts WHERE participant='alice')
                         )
        """)

        assert Participant.from_username('alice').balance == D('10.77')

    def test_ledger_decrements_participant_balance(self):
        self.make_team()
        alice = self.make_participant('alice', balance=20)
        assert alice.balance == D('20.00')

        self.db.run("""
            INSERT INTO ledger
                        (amount, debit, credit)
                 VALUES ( 10.77
                        , (SELECT id FROM accounts WHERE participant='alice')
                        , (SELECT id FROM accounts WHERE team='TheATeam')
                         )
        """)

        assert Participant.from_username('alice').balance == D('9.23')

    def test_ledger_allows_negative_balance(self):
        self.make_team()
        alice = self.make_participant('alice', balance=10)
        assert alice.balance == D('10.00')

        self.db.run("""
            INSERT INTO ledger
                        (amount, debit, credit)
                 VALUES ( 10.77
                        , (SELECT id FROM accounts WHERE participant='alice')
                        , (SELECT id FROM accounts WHERE team='TheATeam')
                         )
        """)

        assert Participant.from_username('alice').balance == D('-0.77')
