from __future__ import absolute_import, division, print_function, unicode_literals

from decimal import Decimal


class StubParticipantAdded(Exception): pass

class MembershipMixin(object):
    """Teams can distribute money to their members.
    """

    def add_member(self, member):
        """Add a member to this team.
        """
        if not member.is_claimed:
            raise StubParticipantAdded
        self.set_take_for(member, Decimal('0.01'), self)

    def remove_member(self, member):
        """Remove a member from this team.
        """
        self.set_take_for(member, Decimal('0.00'), self)

    def remove_all_members(self, cursor=None):
        (cursor or self.db).run("""
            INSERT INTO takes (ctime, member, team, amount, recorder) (
                SELECT ctime, member, %(username)s, 0.00, %(username)s
                  FROM current_takes
                 WHERE team=%(username)s
                   AND amount > 0
            );
        """, dict(username=self.username))

    @property
    def nmembers(self):
        return self.db.one("""
            SELECT COUNT(*)
              FROM current_takes
             WHERE team=%s
        """, (self.username, ))

    def get_members(self, current_participant=None):
        """Return a list of member dicts.
        """
        takes = self.compute_actual_takes()
        members = []
        for take in takes.values():
            member = {}
            member['username'] = take['member']
            member['take'] = take['nominal_amount']
            member['balance'] = take['balance']
            member['percentage'] = take['percentage']

            member['removal_allowed'] = current_participant == self
            member['editing_allowed'] = False
            member['is_current_user'] = False
            if current_participant is not None:
                if member['username'] == current_participant.username:
                    member['is_current_user'] = True
                    if take['ctime'] is not None:
                        # current user, but not the team itself
                        member['editing_allowed']= True

            member['last_week'] = self.get_take_last_week_for(member)
            members.append(member)
        return members
