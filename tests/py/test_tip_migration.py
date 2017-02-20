from __future__ import absolute_import, division, print_function, unicode_literals

import pytest
from gratipay.testing import Harness
from gratipay.models.team.tip_migration import AlreadyMigrated, migrate_all_tips


class Tests(Harness):

    def setUp(self):
        self.admin = self.make_participant('admin', is_admin=True)
        self.alice = self.make_participant('alice', claimed_time='now')
        self.bob = self.make_participant('bob', claimed_time='now')
        self.make_participant('old_team')
        self.make_tip(self.alice, 'old_team', '1.00')
        self.make_tip(self.bob, 'old_team', '2.00')
        self.new_team = self.make_team('new_team', owner='old_team', is_approved=True)

    def setTeamStatus(self, status):
        self.client.POST('/new_team/set-status.json', data={'status': status}, auth_as='admin')

    def capturer(self):
        captured = []
        def capture(line):
            captured.append(line)
        return capture, captured


    # mt - migrate_tips

    def test_mt_migrates_tips_to_payment_instructions(self):
        assert self.new_team.migrate_tips() == 2

        payment_instructions = self.db.all("SELECT * FROM payment_instructions "
                                           "ORDER BY participant_id ASC")
        assert len(payment_instructions) == 2
        assert payment_instructions[0].participant_id == self.alice.id
        assert payment_instructions[0].team_id == self.new_team.id
        assert payment_instructions[0].amount == 1
        assert payment_instructions[1].participant_id == self.bob.id
        assert payment_instructions[1].team_id == self.new_team.id
        assert payment_instructions[1].amount == 2

    def test_mt_only_runs_once(self):
        self.new_team.migrate_tips()
        with pytest.raises(AlreadyMigrated):
            self.new_team.migrate_tips()
        assert len(self.db.all("SELECT * FROM payment_instructions")) == 2

    def test_mt_checks_for_multiple_teams(self):
        self.new_team.migrate_tips()
        newer_team = self.make_team('newer_team', owner='old_team')
        with pytest.raises(AlreadyMigrated):
            newer_team.migrate_tips()
        assert len(self.db.all("SELECT * FROM payment_instructions")) == 2


    # mat - migrate_all_tips

    def test_mat_migrates_all_tips(self):
        capture, captured = self.capturer()
        migrate_all_tips(self.db, capture)
        assert captured == ["Migrated 2 tip(s) for 'new_team'", "Done."]

    def test_mat_ignores_already_migrated_teams(self):
        capture, captured = self.capturer()
        migrate_all_tips(self.db, capture)
        del captured[:]  # clear first run output
        migrate_all_tips(self.db, capture)
        assert captured == ["Done."]

    def test_mat_ignores_unreviewed_teams(self):
        self.setTeamStatus('unreviewed')
        capture, captured = self.capturer()
        migrate_all_tips(self.db, capture)
        assert captured == ["Done."]

    def test_mat_ignores_rejected_teams(self):
        self.setTeamStatus('rejected')
        capture, captured = self.capturer()
        migrate_all_tips(self.db, capture)
        assert captured == ["Done."]
