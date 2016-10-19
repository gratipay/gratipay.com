from datetime import datetime
from decimal import Decimal

from aspen import Response
from psycopg2 import IntegrityError


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
      ORDER BY ts_start ASC
    """, dict(ctime=team.ctime), back_as=dict)
     
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


def export_history(participant, year, mode, key, back_as='namedtuple', require_key=False):
    db = participant.db
    params = dict(username=participant.username, year=year)
    out = {}
    if mode == 'aggregate':
        out['given'] = lambda: db.all("""
            SELECT tippee, sum(amount) AS amount
              FROM transfers
             WHERE tipper = %(username)s
               AND extract(year from timestamp) = %(year)s
          GROUP BY tippee
        """, params, back_as=back_as)
        out['taken'] = lambda: db.all("""
            SELECT tipper AS team, sum(amount) AS amount
              FROM transfers
             WHERE tippee = %(username)s
               AND context = 'take'
               AND extract(year from timestamp) = %(year)s
          GROUP BY tipper
        """, params, back_as=back_as)
    else:
        out['exchanges'] = lambda: db.all("""
            SELECT timestamp, amount, fee, status, note
              FROM exchanges
             WHERE participant = %(username)s
               AND extract(year from timestamp) = %(year)s
          ORDER BY timestamp ASC
        """, params, back_as=back_as)
        out['given'] = lambda: db.all("""
            SELECT timestamp, tippee, amount, context
              FROM transfers
             WHERE tipper = %(username)s
               AND extract(year from timestamp) = %(year)s
          ORDER BY timestamp ASC
        """, params, back_as=back_as)
        out['taken'] = lambda: db.all("""
            SELECT timestamp, tipper AS team, amount
              FROM transfers
             WHERE tippee = %(username)s
               AND context = 'take'
               AND extract(year from timestamp) = %(year)s
          ORDER BY timestamp ASC
        """, params, back_as=back_as)
        out['received'] = lambda: db.all("""
            SELECT timestamp, amount, context
              FROM transfers
             WHERE tippee = %(username)s
               AND context NOT IN ('take', 'take-over')
               AND extract(year from timestamp) = %(year)s
          ORDER BY timestamp ASC
        """, params, back_as=back_as)

    if key:
        try:
            return out[key]()
        except KeyError:
            raise Response(400, "bad key `%s`" % key)
    elif require_key:
        raise Response(400, "missing `key` parameter")
    else:
        return {k: v() for k, v in out.items()}
