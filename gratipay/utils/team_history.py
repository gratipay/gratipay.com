from datetime import datetime
from decimal import Decimal as D

from aspen import Response


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


def iter_payday_events(db, team, year=None):
    """Yields payday events for the given Team.
    """
    current_year = datetime.utcnow().year
    year = year or current_year

    paydays = db.all("""
        SELECT id, ts_start::date
          FROM paydays
         WHERE ts_start > %(ctime)s
           AND extract(year from ts_start) = %(year)s
      ORDER BY id DESC
    """, dict(ctime=team.ctime,year=year), back_as=dict)

    events = []
    events_query = """
        SELECT *
          FROM ( SELECT COALESCE( actual.amount,expected.amount) as amount
                      , COALESCE( expected.participant_id, actual.participant_id ) as participant_id
                      , ( CASE WHEN is_funded IS false then 'No/Invalid Credit Card' end) as Notes
                      , COALESCE( actual.participant, expected.participant) as participant
                      , actual.team
                      , COALESCE(actual.direction, 'to-participant') AS direction
                      , ( CASE when actual.amount is NULL then 'failed' else 'Succeeded' end) as Status
                   FROM ( SELECT DISTINCT ON (participant_id) payment_instructions.*
                             , participants.username as participant
                             , teams.name as team
                         FROM payment_instructions, participants, teams
                        WHERE is_funded = true
                          AND mtime < %(payday_date)s
                          AND team_id = ( SELECT id
                                            FROM teams
                                            WHERE name = %(team)s  )
                          AND participants.id = participant_id
                          AND teams.id = team_id
                        ORDER BY participant_id, team_id, mtime DESC
                       ) expected
                   FULL OUTER JOIN ( SELECT payments.*
                                          , participants.id as participant_id
                                       FROM payments, participants
                                      WHERE payday = %(payday_id)s
                                        AND direction = 'to-team'
                                        AND team = %(team)s
                                        AND participants.username = participant
                                   ) actual
                     ON expected.participant_id = actual.participant_id
                ) received
         UNION ( SELECT COALESCE( actual.amount,expected.amount) as amount
                      , COALESCE( expected.participant_id, actual.participant_id ) as participant_id
                      , ( CASE WHEN expected.amount IS NULL
                          THEN 'Owner Payout'
                          WHEN expected.amount > actual.amount
                          THEN 'Not Enough Funds'
                          ELSE '' END
                        ) as Notes
                      , COALESCE( actual.participant, expected.participant) as participant
                      , actual.team
                      , COALESCE(actual.direction, 'to-team') AS direction
                      , (CASE when actual.amount is NULL then 'failed' else 'Succeeded' end) as Status
                   FROM ( SELECT DISTINCT ON (participant_id) takes.*
                               , participants.username as participant
                               , teams.name as team
                            FROM takes, participants, teams
                           WHERE mtime < %(payday_date)s
                             AND team_id = ( SELECT id
                                               FROM teams
                                              WHERE name = %(team)s )
                             AND participants.id = participant_id
                             AND teams.id = team_id
                           ORDER BY participant_id, team_id, mtime DESC
                        ) expected
                   FULL OUTER JOIN ( SELECT payments.*
                                          , participants.id as participant_id
                                       FROM payments, participants
                                      WHERE payday = %(payday_id)s
                                        AND direction = 'to-participant'
                                        AND team = %(team)s
                                        AND participants.username = participant
                                    ) actual
                   ON expected.participant_id = actual.participant_id )
         ORDER BY direction"""

    for payday in paydays:
        payday_events = db.all(events_query
                              , dict(team=team.name
                                    , payday_id=payday['id']
                                    , payday_date=payday['ts_start'])
                              , back_as=dict)

        events.append (dict(id=payday['id'], date=payday['ts_start'], events=payday_events))

    return events
