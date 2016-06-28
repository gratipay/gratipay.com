from __future__ import absolute_import, division, print_function, unicode_literals

from decimal import Decimal as D


PENNY = D('0.01')
ZERO = D('0.00')


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


    def set_take_for(self, participant, take, recorder):
        """Set the amount a participant wants to take from this team during payday.

        :param Participant participant: the participant to set the take for
        :param int take: the amount the participant wants to take
        :param Participant recorder: the participant making the change

        :return: ``None``
        :raises: :py:exc:`NotAllowed`

        It is a bug to pass in a ``participant`` or ``recorder`` that is
        suspicious, unclaimed, or without a verified email and identity.
        Furthermore, :py:exc:`NotAllowed` is raised in the following circumstances:

        - ``recorder`` is neither ``participant`` nor the team owner
        - ``recorder`` is the team owner and ``take`` is neither zero nor $0.01
        - ``recorder`` is ``participant``, but ``participant`` isn't already on the team

        """
        def vet(p):
            assert not p.is_suspicious, p.id
            assert p.is_claimed, p.id
            assert p.email_address, p.id
            assert p.has_verified_identity, p.id

        vet(participant)
        vet(recorder)

        if recorder.username == self.owner:
            if take not in (ZERO, PENNY):
                raise NotAllowed('owner can only add and remove members, not otherwise set takes')
        elif recorder != participant:
            raise NotAllowed('can only set own take')

        with self.db.get_cursor() as cursor:

            cursor.run("LOCK TABLE takes IN EXCLUSIVE MODE")  # avoid race conditions

            old_take = self.get_take_for(participant, cursor=cursor)
            if recorder.username != self.owner:
                if recorder == participant and not old_take:
                    raise NotAllowed('can only set take if already a member of the team')

            ndistributing_to = self.ndistributing_to

            if old_take and not take:
                ndelta = -1
            elif not old_take and take:
                ndelta = 1
            else:
                ndelta = 0

            ndistributing_to += ndelta
            delta = take - old_take

            cursor.run( "UPDATE teams SET ndistributing_to=%s WHERE id=%s"
                      , (ndistributing_to, self.id)
                       )

            cursor.one( """

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
                  RETURNING *

            """, { 'participant_id': participant.id
                 , 'team_id': self.id
                 , 'amount': take
                 , 'recorder_id': recorder.id
                  })

            self.set_attributes(ndistributing_to=ndistributing_to)

            taking, ntaking_from = cursor.one("""

                UPDATE participants
                   SET taking=taking+%s, ntaking_from=ntaking_from+%s
                 WHERE id=%s
             RETURNING taking, ntaking_from

            """ , (delta, ndelta, participant.id))

            participant.set_attributes(taking=taking, ntaking_from=ntaking_from)


    def get_take_for(self, participant, cursor=None):
        """
        :param Participant participant: the participant to get the take for
        :param GratipayDB cursor: a database cursor; if ``None``, a new cursor will be used
        :return: the ``participant``'s take from this team, as a :py:class:`~decimal.Decimal`
        """
        return (cursor or self.db).one("""

            SELECT amount
              FROM current_takes
             WHERE team_id=%s AND participant_id=%s

        """, (self.id, participant.id), default=ZERO)


class NotAllowed(Exception):
    """Raised by :py:meth:`set_take_for` if ``recorder`` is not allowed to set
    the take for ``participant``.
    """
