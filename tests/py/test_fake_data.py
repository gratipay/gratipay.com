from __future__ import print_function, unicode_literals

from gratipay.utils import fake_data
from gratipay.testing import Harness


class TestFakeData(Harness):
    """
    Ensure the fake_data script doesn't throw any exceptions
    """

    def test_fake_data(self):
        nparticipants = 5
        ntips = 5
        nteams = 1
        ntransfers = 5
        fake_data.populate_db(self.db, nparticipants, ntips, nteams, ntransfers)
        tips = self.db.all("SELECT * FROM tips")
        participants = self.db.all("SELECT * FROM participants")
        teams = self.db.all("SELECT * FROM teams")
        transfers = self.db.all("SELECT * FROM transfers")
        teams = self.db.all("SELECT * FROM teams")
        assert len(tips) == ntips
        assert len(participants) == nparticipants
        assert len(teams) == nteams
        assert len(transfers) == ntransfers
