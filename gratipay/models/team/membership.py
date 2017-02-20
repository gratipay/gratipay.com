from __future__ import absolute_import, division, print_function, unicode_literals

from .takes import ZERO, PENNY


class Membership(object):
    """Teams may have zero or more members, who are participants that take money from the team.
    """

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


    @property
    def nmembers(self):
        """The number of members. Read-only and computed (not in the db); equal to
        :py:attr:`~gratipay.models.team.mixins.takes.ndistributing_to`.
        """
        return self.ndistributing_to


    def get_memberships(self, current_participant=None):
        """Return a list of member dicts.
        """
        takes = self.compute_actual_takes()
        members = []
        for take in takes.values():
            member = {}
            member['participant_id'] = take['participant'].id
            member['username'] = take['participant'].username
            member['take'] = take['nominal_amount']
            member['balance'] = take['balance']
            member['percentage'] = take['percentage']

            member['editing_allowed'] = False
            member['is_current_user'] = False
            if current_participant:
                member['removal_allowed'] = current_participant.username == self.owner
                if member['username'] == current_participant.username:
                    member['editing_allowed']= True

            member['last_week'] = self.get_take_last_week_for(take['participant'])
            members.append(member)
        return members
