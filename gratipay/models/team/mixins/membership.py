from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.models.team.mixins.takes import ZERO, PENNY


class MembershipMixin(object):
    """Teams may have zero or more members.
    """


    @property
    def nmembers(self):
        """The number of members. Read-only and computed (not in the db); equal to
        :py:attr:`~gratipay.models.team.mixins.takes.ndistributing_to`.
        """
        return self.ndistributing_to


    def get_memberships(self, cursor=None):
        """Return a list of membership records for this team.
        """
        return (cursor or self.db).all("""

            SELECT ct.*
                 , (SELECT p.*::participants
                      FROM participants p
                     WHERE p.id=participant_id) AS participant
              FROM current_takes ct
              JOIN teams t
                ON t.id = ct.team_id
             WHERE t.id = %s
               AND ct.amount > 0

        """, (self.id,))


    def add_member(self, participant, recorder):
        """Add a participant to this team.

        :param Participant participant: the participant to add
        :param Participant recorder: the participant making the change

        """
        self.set_take_for(participant, PENNY, recorder)


    def remove_member(self, participant, recorder):
        """Remove a participant from this team.

        :param Participant participant: the participant to remove
        :param Participant recorder: the participant making the change

        """
        self.set_take_for(participant, ZERO, recorder)
