"""Teams on Gratipay are plural participants with members.
"""
from collections import OrderedDict
from decimal import Decimal

from postgres.orm import Model

class MemberLimitReached(Exception): pass

class StubParticipantAdded(Exception): pass

class Team(Model):
    """Represent a Gratipay team.
    """

    typname = 'teams'


    # Constructors
    # ============

    @classmethod
    def from_id(cls, id):
        """Return an existing team based on id.
        """
        return cls._from_thing("id", id)

    @classmethod
    def from_slug(cls, slug):
        """Return an existing team based on slug.
        """
        return cls._from_thing("slug_lower", slug.lower())

    @classmethod
    def _from_thing(cls, thing, value):
        assert thing in ("id", "slug_lower")
        return cls.db.one("""

            SELECT teams.*::teams
              FROM teams
             WHERE {}=%s

        """.format(thing), (value,))

    @classmethod
    def create_new(cls, owner, fields):
        return cls.db.one("""

            INSERT INTO teams
                        (slug, slug_lower, name, homepage, product_or_service,
                         getting_involved, getting_paid, owner)
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
              RETURNING teams.*::teams

        """, (fields['slug'], fields['slug'].lower(), fields['name'], fields['homepage'],
              fields['product_or_service'], fields['getting_involved'], fields['getting_paid'],
              owner.username))


    # Members
    # =======

    def add_member(self, member):
        """Add a member to this team.
        """
        if len(self.get_current_takes()) == 149:
            raise MemberLimitReached
        if not member.is_claimed:
            raise StubParticipantAdded
        self.__set_take_for(member, Decimal('0.01'), self.owner)

    def remove_member(self, member):
        """Remove a member from this team.
        """
        self.__set_take_for(member, Decimal('0.00'), self.owner)

    def remove_all_members(self, cursor=None):
        (cursor or self.db).run("""
            INSERT INTO payroll
                        (ctime, member, team, amount, recorder)
                        (
                            SELECT ctime, member, %(team)s, 0.00, %(recorder)s
                              FROM current_payroll
                             WHERE team=%(team)s
                               AND amount > 0
                        );
        """, dict(team=self.slug, recorder=self.owner))

    @property
    def nmembers(self):
        return self.db.one("""
            SELECT COUNT(*)
              FROM current_payroll
             WHERE team=%s
        """, (self.slug, ))

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

            member['removal_allowed'] = (current_participant.username == self.owner)
            member['editing_allowed'] = False
            member['is_current_user'] = False
            if current_participant is not None:
                if member['username'] == current_participant.username:
                    member['is_current_user'] = True
                    if take['ctime'] is not None:
                        # current user, but not the team itself
                        member['editing_allowed']= True

            member['last_week'] = last_week = self.get_take_last_week_for(member)
            member['max_this_week'] = self.compute_max_this_week(last_week)
            members.append(member)
        return members


    # Takes
    # =====

    def get_take_last_week_for(self, member):
        """Get the user's nominal take last week. Used in throttling.
        """
        membername = member.username if hasattr(member, 'username') else member['username']
        return self.db.one("""

            SELECT amount
              FROM payroll
             WHERE team=%s AND member=%s
               AND mtime < (
                       SELECT ts_start
                         FROM paydays
                        WHERE ts_end > ts_start
                     ORDER BY ts_start DESC LIMIT 1
                   )
          ORDER BY mtime DESC LIMIT 1

        """, (self.slug, membername), default=Decimal('0.00'))

    def get_take_for(self, member):
        """Return a Decimal representation of the take for this member, or 0.
        """
        return self.db.one("""

            SELECT amount
              FROM current_payroll
             WHERE member=%s
               AND team=%s

        """, (member.username, self.slug), default=Decimal('0.00'))

    def compute_max_this_week(self, last_week):
        """2x last week's take, but at least a dollar.
        """
        return max(last_week * Decimal('2'), Decimal('1.00'))

    def set_take_for(self, member, take, recorder, cursor=None):
        """Sets member's take from the team pool.
        """

        assert hasattr(member, 'username')
        assert recorder == self.owner or hasattr(recorder, 'username')
        assert isinstance(take, Decimal)

        last_week = self.get_take_last_week_for(member)
        max_this_week = self.compute_max_this_week(last_week)
        if take > max_this_week:
            take = max_this_week

        self.__set_take_for(member, take, recorder, cursor)
        return take

    def __set_take_for(self, member, amount, recorder, cursor=None):
        # XXX Factored out for testing purposes only! :O Use .set_take_for.
        with self.db.get_cursor(cursor) as cursor:
            # Lock to avoid race conditions
            cursor.run("LOCK TABLE payroll IN EXCLUSIVE MODE")
            # Compute the current takes
            old_takes = self.compute_actual_takes(cursor)
            # Insert the new take
            recordername = recorder.username if hasattr(recorder, 'username') else recorder
            cursor.run("""

                INSERT INTO payroll (ctime, member, team, amount, recorder)
                     VALUES ( COALESCE (( SELECT ctime
                                            FROM payroll
                                           WHERE member=%(member)s
                                             AND team=%(team)s
                                           LIMIT 1
                                         ), CURRENT_TIMESTAMP)
                            , %(member)s
                            , %(team)s
                            , %(amount)s
                            , %(recorder)s
                            )

            """, dict(member=member.username, team=self.slug, amount=amount,
                      recorder=recordername))
            # Compute the new takes
            new_takes = self.compute_actual_takes(cursor)
            # Update receiving amounts in the participants table
            self.update_taking(old_takes, new_takes, cursor, member)
            # Update is_funded on member's tips
            member.update_giving(cursor)

    def update_taking(self, old_takes, new_takes, cursor=None, member=None):
        """Update `taking` amounts based on the difference between `old_takes`
        and `new_takes`.
        """
        for username in set(old_takes.keys()).union(new_takes.keys()):
            if username == self.slug:
                continue
            old = old_takes.get(username, {}).get('actual_amount', Decimal(0))
            new = new_takes.get(username, {}).get('actual_amount', Decimal(0))
            diff = new - old
            if diff != 0:
                r = (cursor or self.db).one("""
                    UPDATE participants
                       SET taking = (taking + %(diff)s)
                         , receiving = (receiving + %(diff)s)
                     WHERE username=%(username)s
                 RETURNING taking, receiving
                """, dict(username=username, diff=diff))
                if member and username == member.username:
                    member.set_attributes(**r._asdict())

    def get_current_takes(self, cursor=None):
        """Return a list of member takes for a team.
        """
        TAKES = """
            SELECT member, amount, ctime, mtime
              FROM current_payroll
             WHERE team=%(team)s
          ORDER BY ctime DESC
        """
        records = (cursor or self.db).all(TAKES, dict(team=self.slug))
        return [r._asdict() for r in records]

    def get_team_take(self, cursor=None):
        """Return a single take for a team, the team itself's take.
        """
        TAKE = "SELECT sum(amount) FROM current_payroll WHERE team=%s"
        total_take = (cursor or self.db).one(TAKE, (self.slug,), default=0)
        team_take = max(self.receiving - total_take, 0)
        membership = { "ctime": None
                     , "mtime": None
                     , "member": self.slug
                     , "amount": team_take
                      }
        return membership

    def compute_actual_takes(self, cursor=None):
        """Get the takes, compute the actual amounts, and return an OrderedDict.
        """
        actual_takes = OrderedDict()
        nominal_takes = self.get_current_takes(cursor=cursor)
        nominal_takes.append(self.get_team_take(cursor=cursor))
        budget = balance = self.receiving
        for take in nominal_takes:
            nominal_amount = take['nominal_amount'] = take.pop('amount')
            actual_amount = take['actual_amount'] = min(nominal_amount, balance)
            if take['member'] != self.slug:
                balance -= actual_amount
            take['balance'] = balance
            take['percentage'] = (actual_amount / budget) if budget > 0 else 0
            actual_takes[take['member']] = take
        return actual_takes

    # Cached amounts
    # ==============

    def update_receiving(self, cursor=None):
        old_takes = self.compute_actual_takes(cursor=cursor)

        receiving, nsupporters = (cursor or self.db).one("""
            WITH active_subscriptions AS (
                SELECT amount
                  FROM current_subscriptions s
                  JOIN teams t2 ON t2.slug = s.team
                  JOIN participants p ON p.username = s.subscriber
                 WHERE team=%(slug)s
                   AND amount > 0
                   AND is_funded
                   AND t2.is_approved
                   AND p.is_suspicious IS NOT TRUE
            )
            UPDATE teams t
               SET receiving = COALESCE((
                      SELECT sum(amount)
                        FROM active_subscriptions
                   ), 0),
                   nsupporters = COALESCE((SELECT count(*) FROM active_subscriptions), 0)
             WHERE t.slug=%(slug)s
         RETURNING receiving, nsupporters
        """, dict(slug=self.slug))

        self.set_attributes(receiving=receiving, nsupporters=nsupporters)

        new_takes = self.compute_actual_takes(cursor=cursor)
        self.update_taking(old_takes, new_takes, cursor=cursor)
