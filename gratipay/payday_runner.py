# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import aspen
from psycopg2 import IntegrityError

from gratipay.billing.payday import Payday


class PaydayRunner(object):
    """The Gratipay application can start a weekly payday process.
    """

    def __init__(self, app):
        self.app = app


    def run_payday(self):
        """Run Gratipay's weekly payday.

        If there is a Payday that hasn't finished yet, then the UNIQUE
        constraint on ts_end will kick in and notify us of that. In that case
        we load the existing Payday and work on it some more. We use the start
        time of the current Payday to synchronize our work.

        """
        self._start_payday().run()


    def _start_payday(self):
        try:
            d = self.app.db.one("""
                INSERT INTO paydays DEFAULT VALUES
                RETURNING id, (ts_start AT TIME ZONE 'UTC') AS ts_start, stage
            """, back_as=dict)
            aspen.log("Starting a new payday.")
        except IntegrityError:  # Collision, we have a Payday already.
            d = self.app.db.one("""
                SELECT id, (ts_start AT TIME ZONE 'UTC') AS ts_start, stage
                  FROM paydays
                 WHERE ts_end='1970-01-01T00:00:00+00'::timestamptz
            """, back_as=dict)
            aspen.log("Picking up with an existing payday.")

        d['ts_start'] = d['ts_start'].replace(tzinfo=aspen.utils.utc)

        aspen.log("Payday started at %s." % d['ts_start'])

        payday = Payday(self)
        payday.__dict__.update(d)
        return payday
