from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.models import add_event


class TakesMixin(object):
    """This mixin provides API for working with
    :py:class:`~gratipay.models.team.Team` takes, which is used by the
    :py:class:`~gratipay.models.team.mixins.Membership` mixin.

    Teams may issue "takes," which are like shares but different. Shares confer
    legal ownership. Membership in a Gratipay team does not confer legal
    ownership---though a team's legal owners may "claim" takes, right alongside
    employees, contractors, etc. Takes determines how money is split each week.

    """

    #: The total number of takes issued for this team. Read-only;
    #: modified by :py:meth:`set_ntakes`.

    ntakes = 0


    #: The aggregate number of takes that have been claimed by team members.
    #: Read-only; modified by :py:meth:`set_ntakes_for`.

    ntakes_claimed = 0


    #: The number of takes that have yet to be claimed by any team member.
    #: Read-only; modified by :py:meth:`set_ntakes` and
    #: :py:meth:`set_ntakes_for`.

    ntakes_unclaimed = 0


    def set_ntakes(self, ntakes):
        """Set the total number of takes for this team.

        :param int ntakes: the target number of takes

        :return: the number of takes actually set

        This method does not alter claimed takes, so it has the effect of
        diluting or concentrating membership, depending on whether you are
        increasing or decreasing number of takes (respectively). If you try to
        set the number of takes to fewer than the number of claimed takes, all
        existing unclaimed takes are withdrawn, but claimed takes remain. If
        there are no claimed takes, and you try to set the number of
        outstanding takes lower than zero, it is set to zero.

        """
        with self.db.get_cursor() as cursor:

            new_ntakes, new_ntakes_unclaimed = cursor.one("""

                UPDATE teams
                   SET ntakes = greatest(0, ntakes_claimed, %(ntakes)s)
                     , ntakes_unclaimed = greatest(0, ntakes_claimed, %(ntakes)s) - ntakes_claimed
                 WHERE id=%(team_id)s
             RETURNING ntakes, ntakes_unclaimed

            """, dict(ntakes=ntakes, team_id=self.id))

            add_event( cursor
                     , 'team'
                     , dict( id=self.id
                           , action='outstanding takes changed'
                           , old={'ntakes': self.ntakes, 'ntakes_unclaimed': self.ntakes_unclaimed}
                           , new={'ntakes': new_ntakes, 'ntakes_unclaimed': new_ntakes_unclaimed}
                            )
                      )

            self.set_attributes(ntakes=new_ntakes, ntakes_unclaimed=new_ntakes_unclaimed)

        return self.ntakes


    def set_ntakes_for(self, participant, ntakes, recorder=None):
        """Set the number of takes claimed by a given participant.

        :param Participant participant: the participant to set the number of claimed takes for
        :param int ntakes: the number of takes

        :return: the number of takes actually assigned

        This method will try to set the given participant's total number of
        claimed takes to ``ntakes``, or as many as possible, if there are not
        enough unclaimed takes that is less than ``ntakes``.

        It is a bug to pass in a participant that is suspicous, unclaimed, or
        without a verified email and identity.

        """
        assert not participant.is_suspicious, participant.id
        assert participant.is_claimed, participant.id
        assert participant.email_address, participant.id
        assert participant.has_verified_identity, participant.id

        recorder = recorder or participant

        with self.db.get_cursor() as cursor:

            old_ntakes = cursor.one("""
                SELECT ntakes FROM takes WHERE participant_id=%s ORDER BY mtime DESC LIMIT 1
            """, (participant.id,))

            nmembers = self.nmembers
            nclaimed = self.ntakes_claimed
            nunclaimed = self.ntakes_unclaimed

            if old_ntakes:
                nclaimed -= old_ntakes
                nunclaimed += old_ntakes
            else:
                nmembers += 1

            ntakes = min(ntakes, nunclaimed)

            if ntakes:
                nunclaimed -= ntakes
                nclaimed += ntakes
            else:
                nmembers -= 1

            cursor.run("""

                UPDATE teams
                   SET ndistributing_to=%s
                     , ntakes_claimed=%s
                     , ntakes_unclaimed=%s
                 WHERE id=%s

            """, (nmembers, nclaimed, nunclaimed, self.id))

            cursor.run( """

                INSERT INTO takes
                            (ctime, participant_id, team_id, ntakes, recorder_id)
                     VALUES ( COALESCE (( SELECT ctime
                                            FROM takes
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

            self.set_attributes( ntakes_claimed=nclaimed
                               , ntakes_unclaimed=nunclaimed
                               , ndistributing_to=nmembers
                                )

            return ntakes
