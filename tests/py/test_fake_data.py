from __future__ import print_function, unicode_literals

from gratipay.utils import fake_data
from gratipay.testing import Harness


class TestFakeData(Harness):
    """
    Ensure the fake_data script doesn't throw any exceptions
    """
    def test_fake_data(self):
        num_participants = 6
        num_tips = 25
        num_teams = 5
        fake_data.main(self.db, num_participants, num_tips, num_teams)
        participants = self.db.all("SELECT * FROM participants")
        teams = self.db.all("SELECT * FROM teams")
        payment_instructions = self.db.all("SELECT * FROM payment_instructions")
        assert len(participants) == num_participants
        assert len(teams) == num_teams + 1      # +1 for the fake Gratipay team.
        assert len(payment_instructions) == num_tips


    def test_fake_participant_identity(self):
        crusher = self.make_participant('crusher', email_address='crusher@example.com')
        country_id = fake_data.fake_participant_identity(crusher)
        assert [x.country.id for x in crusher.list_identity_metadata()] == [country_id]

    def test_fake_team_doesnt_fail_for_name_with_apostrophe(self):
        crusher = self.make_participant('crusher', email_address='crusher@example.com')
        team = fake_data.fake_team(self.db, crusher, "D'Amorebury") 
        assert team.name != "d-amorebury"
