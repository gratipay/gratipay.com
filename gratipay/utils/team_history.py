# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from itertools import groupby

def get_end_of_year_totals(db, team, year):
    """Gets the year end received and distributed for a team

       Arguments:
       team -- The Team object for the year end totals being returned.
       year -- The integer year of the totals being returned.
    """

    received = db.one("""
        SELECT COALESCE(sum(amount), 0) AS Received
          FROM payments
         WHERE team = %(team)s
           AND extract(year from timestamp) = %(year)s
           AND amount > 0
           AND direction='to-team';
    """, dict(team=team.slug, year=year) )

    distributed = db.one("""
        SELECT COALESCE(sum(amount), 0) AS Distributed
          FROM payments
         WHERE team = %(team)s
           AND extract(year from timestamp) = %(year)s
           AND amount > 0
           AND direction='to-participant';
    """, dict(team=team.slug, year=year) )

    return received, distributed


def iter_team_payday_events(db, team, year):
    """Yields payday events for the given Team.

       Arguments:
       team -- The Team object that the events are being iterated.
       year -- The integer year for the events being iterated.
    """

    payments = db.all("""
        SELECT payments.*, paydays.ts_start as payday_start
          FROM payments
          JOIN paydays
            ON payments.payday = paydays.id
           AND team=%(team)s
           AND extract(year from timestamp) = %(year)s
         ORDER BY payments.payday DESC, direction, amount DESC
       """, dict(team=team.slug, year=year), back_as=dict)

    events = []

    grouped_payments = groupby(payments, lambda x: (x['payday'], x['payday_start']))
    for (payday_id, payday_start), _payments in grouped_payments:
        events.append(dict(id=payday_id, date=payday_start, events=list(_payments)))

    return events
    """
    payday_id = payments[0]['payday']
    payday_date = payments[0]['payday_start']
    payday_events = []

    if not payments:
        return payments


    for payment in payments:
        if payment['payday'] != payday_id:
            events.append (dict(id=payday_id, date=payment['payday_start'], events=payday_events))
            payday_id = payment['payday']
            payday_date = payment['payday_start']
            payday_events = []

        payday_events.append(payment)

    events.append (dict(id=payday_id, date=payday_date, events=payday_events))

    return events
    """
