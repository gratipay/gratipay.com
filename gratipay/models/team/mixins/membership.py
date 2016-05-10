from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.models import add_event


class NoRoom(Exception):
    pass


class MembershipMixin(object):
    """This mixin provides membership management for
    :py:class:`~gratipay.models.team.Team` objects.
    """

    @property
    def nmembers(self):
        return self.ndistributing_to


    def set_takes_enabled(self, to):
        """Update whether takes are enabled for this team.

        :param bool to: whether the team should have takes enabled

        """
        if type(to) is not bool:
            raise TypeError('Boolean required.')
        with self.db.get_cursor() as cursor:
            cursor.run("UPDATE teams SET takes_enabled=%s WHERE id=%s", (to, self.id))
            add_event( cursor
                     , 'team'
                     , dict( action='set takes_enabled'
                           , id=self.id
                           , old_value=self.takes_enabled
                           , new_value=to
                            )
                      )


    def get_memberships(self, cursor=None):
        """Return a list of memberships for this team.
        """
        return (cursor or self.db).all("""
            SELECT *
                 , (SELECT p.*::participants
                      FROM participants p
                     WHERE id=participant_id) AS participant
              FROM current_memberships
             WHERE id=%s
        """, (self.id,))


    def update_membership(self, participant, ntakes, recorder=None):
        """Set the number of takes for a given participant.

        :param Participant participant: the participant to set the number of takes for
        :param int ntakes: the number of takes

        :return: the number of takes actually assigned

        Each Team has 1,000 takes in total. This method will claim _up to_
        ``ntakes`` takes for the given participants.

        """
        recorder = recorder or participant
        with self.db.get_cursor() as cursor:
            memberships = self.get_memberships(cursor)

            nremaining = 1000
            nclaimed = 0
            nmembers = 0
            membership = None
            for _membership in memberships:
                nremaining -= _membership.ntakes
                nclaimed += _membership.ntakes
                nmembers += 1
                if membership.participant_id == participant.id:
                    membership = _membership
                    break

            # sanity checks ...
            assert nremaining == self.ntakes_remaining, (nremaining, self.ntakes_remaining)
            assert nclaimed == self.ntakes_claimed, (nclaimed, self.ntakes_claimed)
            assert nmembers == self.nmembers, (nmembers, self.nmembers)
            assert participant.is_claimed, participant.id
            assert participant.has_verified_identity, participant.id
            assert participant.email_address, participant.id
            assert not participant.is_suspicious, participant.id

            if membership:
                nclaimed -= membership.ntakes
                nremaining += membership.ntakes
            ntakes = min(ntakes, nremaining)
            nremaining -= ntakes
            nclaimed += ntakes

            cursor.run("""

                UPDATE teams
                   SET ntakes_claimed=%s
                     , ntakes_remaining=%s
                     , nmembers=%s
                 WHERE id=%s

            """, (nclaimed, nremaining, nmembers, self.id))

            cursor.run( """

                INSERT INTO memberships
                            (ctime, participant_id, team_id, ntakes, recorder_id)
                     VALUES ( COALESCE (( SELECT ctime
                                            FROM memberships
                                           WHERE (participant_id=%(participant_id)s
                                                  AND team_id=%(team_id)s)
                                           LIMIT 1
                                         ), CURRENT_TIMESTAMP)
                            , %(participant_id)s, %(team_id)s, %(ntakes)s, %(recorder_id)s
                             )

            """, { 'participant_id': participant.id
                 , 'team_id': self.id
                 , 'ntakes': ntakes
                 , 'recorder_id': recorder.id
                  })

            self.set_attributes(ntakes_claimed=nclaimed, ntakes_remaining=nremaining)

            return ntakes


    def add_member(self, participant):
        """Add a participant to this team.

        :param Participant participant: the participant to add

        """
        ntakes = self.update_membership(participant, 1)
        if ntakes == 0:
            raise NoRoom


    def remove_member(self, participant):
        """Remove a participant from this team.

        :param Participant participant: the participant to remove

        """
        self.update_membership(participant, 0)
