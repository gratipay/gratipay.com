# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from datetime import datetime
from decimal import Decimal as D


def get_end_of_year_totals(db, team, year):

    received = db.one("""
        SELECT COALESCE(sum(amount), 0) AS Received
          FROM payments
         WHERE team = %(team)s
           AND extract(year from timestamp) = %(year)s
           AND amount > 0
           AND direction='to-team';
    """, locals() )

    if received is None:
       received = D(0.00)

    distributed = db.one("""
        SELECT COALESCE(sum(amount), 0) AS Distributed
          FROM payments
         WHERE team = %(team)s
           AND extract(year from timestamp) = %(year)s
           AND amount > 0
           AND direction='to-participant';
    """, locals())

    if distributed is None:
        distributed = D(0.00)

    return received, distributed


def iter_team_payday_events(db, team, year=None):
    """Yields payday events for the given Team.
    """
    current_year = datetime.utcnow().year
    year = year or current_year

    payments = db.all("""
        SELECT payments.*, paydays.ts_start
          FROM payments, paydays
         WHERE payments.payday = paydays.id
           AND team=%(team)s
           AND extract(year from timestamp) = %(year)s
         ORDER BY payments.payday, direction, amount DESC
       """, dict(team=team.slug, year=year), back_as=dict)

    events = []
    payday_id = payments[0]['payday']
    payday_date = payments[0]['ts_start']
    payday_events = []

    if not payments:
        return payments

    #return payments

    for payment in payments:
        if payment['payday'] != payday_id:
            events.append (dict(id=payday_id, date=payment['ts_start'], events=payday_events))
            payday_id = payment['payday']
            payday_date = payment['ts_start']
            payday_events = []

        payday_events.append(payment)

    events.append (dict(id=payday_id, date=payday_date, events=payday_events))

    return events
