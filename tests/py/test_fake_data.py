from __future__ import print_function, unicode_literals

from gratipay.utils import fake_data
from gratipay.testing import Harness


class TestFakeData(Harness):
    """
    Ensure the fake_data script doesn't throw any exceptions
    """

    def test_fake_data(self):
        num_participants = 5
        num_tips = 5
        num_teams = 1
        num_transfers = 5
        fake_data.main(self.db, num_participants, num_tips, num_teams, num_transfers)
        tips = self.db.all("SELECT * FROM tips")
        participants = self.db.all("SELECT * FROM participants")
        transfers = self.db.all("SELECT * FROM transfers")
        teams = self.db.all("SELECT * FROM teams")
        payment_instructions = self.db.all("SELECT * FROM payment_instructions")
        assert len(tips) == num_tips
        assert len(participants) == num_participants
        assert len(transfers) == num_transfers
        assert len(teams) == num_teams
        if num_tips <= num_participants - num_teams:
            assert len(payment_instructions) == num_tips
        else:
            assert len(payment_instructions) == (num_participants - num_teams)
