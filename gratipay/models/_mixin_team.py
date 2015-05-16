"""Teams on Gratipay are plural participants with members.
"""

class MemberLimitReached(Exception): pass

class StubParticipantAdded(Exception): pass

class MixinTeam(object):
    """This class provides methods for working with a Participant as a Team.

    :param Participant participant: the underlying :py:class:`~gratipay.participant.Participant` object for this team

    """

    # XXX These were all written with the ORM and need to be converted.

    def __init__(self, participant):
        self.participant = participant

    def show_as_team(self, user):
        """Return a boolean, whether to show this participant as a team.
        """
        return False

    def member_of(self, team):
        """Given a Participant object, return a boolean.
        """
        for take in team.get_current_takes():
            if take['member'] == self.username:
                return True
        return False
