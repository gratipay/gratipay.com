from __future__ import absolute_import, division, print_function, unicode_literals

from collections import OrderedDict
from decimal import Decimal as D

ZERO = D('0.00')
PENNY = D('0.01')


class TakesMixin(object):
    """:py:class:`~gratipay.models.participant.Participant` s who are members
    of a :py:class:`~gratipay.models.team.Team` may take money from the team
    during :py:class:`~gratipay.billing.payday.Payday`. Only the team owner may
    add a new member, by setting their take to a penny, but team owners may
    *only* set their take to a penny---no more. Team owners may also remove
    members, by setting their take to zero, as may the members themselves, who
    may also set their take to whatever they wish.
    """

    #: The total amount of money the team distributes to participants
    #: (including the owner) during payday. Read-only; equal to
    #: :py:attr:`~gratipay.models.team.Team.receiving`.

    distributing = 0


    #: The number of participants (including the owner) that the team
    #: distributes money to during payday. Read-only; modified by
    #: :py:meth:`set_take_for`.

    ndistributing_to = 0


    def set_take_for(self, participant, take, recorder, cursor=None):
        """Set the amount a participant wants to take from this team during payday.

        :param Participant participant: the participant to set the take for
        :param Decimal take: the amount the participant wants to take
        :param Participant recorder: the participant making the change

        :return: the new take as a py:class:`~decimal.Decimal`
        :raises: :py:exc:`NotAllowed`

        It is a bug to pass in a ``participant`` or ``recorder`` that is
        suspicious, unclaimed, or without a verified email and identity.
        Furthermore, :py:exc:`NotAllowed` is raised in the following circumstances:

        - ``recorder`` is neither ``participant`` nor the team owner
        - ``recorder`` is the team owner and ``take`` is neither zero nor $0.01
        - ``recorder`` is ``participant``, but ``participant`` isn't already on the team

        """
        def vet(p):
            if p.is_suspicious:
                raise NotAllowed("user must not be flagged as suspicious")
            elif not p.email_address:
                raise NotAllowed("user must have added at least one email address")
            elif not p.has_verified_identity:
                raise NotAllowed("user must have a verified identity")
            elif not p.is_claimed:
                raise NotAllowed("user must have claimed the account")

        vet(participant)
        vet(recorder)

        owner_recording = recorder.username == self.owner
        owner_taking = participant.username == self.owner
        taker_recording = recorder == participant
        adding_or_removing = take in (ZERO, PENNY)

        if owner_recording:
            if not adding_or_removing and not owner_taking:
                raise NotAllowed("owner can only add and remove members, not otherwise set takes")
        elif not taker_recording:
            raise NotAllowed("can only set own take")

        with self.db.get_cursor(cursor) as cursor:
            cursor.run("LOCK TABLE takes IN EXCLUSIVE MODE")  # avoid race conditions

            # Compute the current takes
            old_takes = self.compute_actual_takes(cursor)

            if recorder.username != self.owner:
                if recorder == participant and participant.id not in old_takes:
                    raise NotAllowed("can only set take if already a member of the team")

            new_take = cursor.one( """

                INSERT INTO takes
                            (ctime, participant_id, team_id, amount, recorder_id)
                     VALUES ( COALESCE (( SELECT ctime
                                            FROM takes
                                           WHERE (participant_id=%(participant_id)s
                                                  AND team_id=%(team_id)s)
                                           LIMIT 1
                                         ), CURRENT_TIMESTAMP)
                            , %(participant_id)s, %(team_id)s, %(amount)s, %(recorder_id)s
                             )
                  RETURNING amount

            """, { 'participant_id': participant.id
                 , 'team_id': self.id
                 , 'amount': take
                 , 'recorder_id': recorder.id
                  })

            # Compute the new takes
            all_new_takes = self.compute_actual_takes(cursor)

            # Update computed values
            self.update_taking(old_takes, all_new_takes, cursor, participant)
            self.update_distributing(all_new_takes, cursor)

            return new_take


    def get_take_for(self, participant, cursor=None):
        """
        :param Participant participant: the participant to get the take for
        :param GratipayDB cursor: a database cursor; if ``None``, a new cursor will be used
        :return: a :py:class:`~decimal.Decimal`: the ``participant``'s take from this team, or 0.
        """
        return (cursor or self.db).one("""

            SELECT amount
              FROM current_takes
             WHERE team_id=%s AND participant_id=%s

        """, (self.id, participant.id), default=ZERO)


    def get_take_last_week_for(self, participant, cursor=None):
        """
        :param Participant participant: the participant to get the take for
        :param GratipayDB cursor: a database cursor; if ``None``, a new cursor
            will be used
        :return: a :py:class:`~decimal.Decimal`: the ``participant``'s take
            from this team at the beginning of the last completed payday, or 0.
        """
        return (cursor or self.db).one("""

            SELECT amount
              FROM takes
             WHERE team_id=%s AND participant_id=%s
               AND mtime < (
                       SELECT ts_start
                         FROM paydays
                        WHERE ts_end > ts_start
                     ORDER BY ts_start DESC LIMIT 1
                   )
          ORDER BY mtime DESC LIMIT 1

        """, (self.id, participant.id), default=ZERO)


    def update_taking(self, old_takes, new_takes, cursor=None, member=None):
        """Update `taking` amounts based on the difference between `old_takes`
        and `new_takes`.
        """

        # XXX Deal with owner as well as members

        for participant_id in set(old_takes.keys()).union(new_takes.keys()):
            old = old_takes.get(participant_id, {}).get('actual_amount', ZERO)
            new = new_takes.get(participant_id, {}).get('actual_amount', ZERO)
            delta = new - old
            if delta != 0:
                taking = (cursor or self.db).one("""
                    UPDATE participants
                       SET taking = (taking + %(delta)s)
                     WHERE id=%(participant_id)s
                 RETURNING taking
                """, dict(participant_id=participant_id, delta=delta))
                if member and participant_id == member.id:
                    member.set_attributes(taking=taking)


    def update_distributing(self, new_takes, cursor=None):
        """Update the computed values on the team.
        """
        distributing = sum(t['actual_amount'] for t in new_takes.values())
        ndistributing_to = len(tuple(t for t in new_takes.values() if t['actual_amount'] > 0))

        r = (cursor or self.db).one("""
               UPDATE teams
                  SET distributing=%s, ndistributing_to=%s WHERE id=%s
            RETURNING distributing, ndistributing_to
        """, (distributing, ndistributing_to, self.id))

        self.set_attributes(**r._asdict())


    def get_current_takes(self, cursor=None):
        """Return a list of member takes for a team.
        """
        TAKES = """
            SELECT p.*::participants AS participant
                 , ct.amount, ct.ctime, ct.mtime
              FROM current_takes ct
              JOIN participants p
                ON ct.participant_id = p.id
             WHERE team_id=%(team_id)s
          ORDER BY amount ASC, ctime ASC
        """
        records = (cursor or self.db).all(TAKES, dict(team_id=self.id))
        return [r._asdict() for r in records]


    def compute_actual_takes(self, cursor=None):
        """Get the takes, compute the actual amounts, and return an OrderedDict.
        """
        actual_takes = OrderedDict()
        nominal_takes = self.get_current_takes(cursor=cursor)
        available = balance = self.available
        for take in nominal_takes:
            nominal_amount = take['nominal_amount'] = take.pop('amount')
            actual_amount = take['actual_amount'] = min(nominal_amount, balance)
            take['balance'] = balance = balance - actual_amount
            take['percentage'] = actual_amount / available
            actual_takes[take['participant'].id] = take
        return actual_takes


class NotAllowed(Exception):
    """Raised by :py:meth:`set_take_for` if ``recorder`` is not allowed to set
    the take for ``participant``.
    """
