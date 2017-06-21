from __future__ import absolute_import, division, print_function, unicode_literals

import datetime

from gratipay.testing import Harness
from gratipay.utils.team_history import get_end_of_year_totals, iter_team_payday_events


def make_history(harness):
    # Make Participants
    alice = harness.make_participant('alice', claimed_time=datetime.datetime(2010, 1, 1, 0, 0, 0))
    picard = harness.make_participant('picard', claimed_time=datetime.datetime(2010, 1, 1, 0, 0, 0))
    bob = harness.make_participant('bob', claimed_time=datetime.datetime(2010, 2, 1, 0, 0, 0), is_admin=True)
    harness.alice = alice
    harness.picard = picard
    harness.bob = bob

    # Make team
    enterprise = harness.make_team('The Enterprise', ctime=datetime.datetime(2010, 1, 2, 0, 0, 0), owner=picard, is_approved=True)
    harness.enterprise = enterprise

    # Make paydays (about 4)
    date = datetime.datetime(2010, 2, 1, 0, 0, 0)
    for i in xrange(3):
        end_date = date + datetime.timedelta(days=6)

        # Need to create the payday record before inserting payment records
        params = dict(ts_start=date, ts_end=end_date)
        with harness.db.get_cursor() as cursor:
            payday_id = cursor.one("""
                    INSERT INTO paydays
                                (ts_start, ts_end)
                         VALUES (%(ts_start)s, %(ts_end)s)
                      RETURNING id
                    """, params)
        # Make payments
        harness.make_payment(alice, enterprise, 50, 'to-team', payday_id, timestamp=date)
        harness.make_payment(bob, enterprise, 25, 'to-team', payday_id , timestamp=date)
        harness.make_payment(picard, enterprise, 50, 'to-participant', payday_id , timestamp=date)
        date = end_date

class TestTeamHistory(Harness):

    def test_iter_team_payment_events(self):
        end_date = datetime.datetime.now()
        alice = self.make_participant('alice', claimed_time=datetime.datetime(2010, 1, 1, 0, 0, 0))
        picard = self.make_participant('picard', claimed_time=datetime.datetime(2010, 1, 1, 0, 0, 0))

        enterprise = self.make_team('The Enterprise', owner=picard, is_approved=True)

        # Need to create the payday record before inserting payment records
        date = end_date - datetime.timedelta(days=7)
        params = dict(ts_start=date, ts_end=end_date)
        with self.db.get_cursor() as cursor:
            payday_id = cursor.one("""
                    INSERT INTO paydays
                                (ts_start, ts_end)
                         VALUES (%(ts_start)s, %(ts_end)s)
                      RETURNING id
                    """, params)

        # Think would be considered sanity check, no records should exist
        #payments = iter_team_payday_events(self.db, enterprise)
        #assert not payments

        self.make_payment(alice.username, enterprise.slug, 50, 'to-team', payday_id, timestamp=date)
        self.make_payment(picard.username, enterprise.slug, 25, 'to-participant', payday_id , timestamp=date)
        payments = iter_team_payday_events(self.db, enterprise, datetime.datetime.utcnow().year)
        assert len(payments) == 1
        assert len(payments[0]['events']) == 2
        assert payments[0]['events'][0]['amount'] == 50
        assert payments[0]['events'][0]['direction'] == 'to-team'
        assert payments[0]['events'][1]['amount'] == 25
        assert payments[0]['events'][1]['direction'] == 'to-participant'
        assert payments[0]['id'] == payments[0]['events'][0]['payday']
        assert payments[0]['date'] == payments[0]['events'][0]['payday_start']  # !?!


    def test_get_end_of_year_totals(self):
        make_history(self)
        balance = get_end_of_year_totals(self.db, team=self.enterprise, year='2010' )
        assert balance[0] == 225
        assert balance[1] == 150


class TestTeamHistoryPage(Harness):

    def setUp(self):
        Harness.setUp(self)
        make_history(self)

    def test_owner_can_view_team_history(self):
        assert self.client.GET('/TheEnterprise/history/?year=2010', auth_as='picard').code == 200

    def test_admin_can_view_team_history(self):
        assert self.client.GET('/TheEnterprise/history/?year=2010', auth_as='bob').code == 200

    def test_nonower_cannot_view_team_history(self):
        assert self.client.GxT('/TheEnterprise/history/?year=2010', auth_as='alice').code == 403

    def test_anon_cannot_view_team_history(self):
        assert self.client.GxT('/TheEnterprise/history/?year=2010').code == 401

    def test_bad_year_for_team_history(self):
        assert self.client.GxT('/TheEnterprise/history/?year=2009', auth_as='picard').code == 400
