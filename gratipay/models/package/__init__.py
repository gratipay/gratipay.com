from gratipay.models.team import Team

from postgres.orm import Model

class Package(Model):
    """Represent a gratipackage. :-)
    """

    typname = 'packages'

    def __eq__(self, other):
        if not isinstance(other, Package):
            return False
        return self.id == other.id

    def __ne__(self, other):
        if not isinstance(other, Package):
            return True
        return self.id != other.id

    # Constructors
    # ============

    @classmethod
    def from_id(cls, id):
        """Return an existing package based on id.
        """
        return cls._from_thing("id", id)

    @classmethod
    def from_team_slug(cls, slug):
        """Return an existing package based on team's slug.
        """
        return cls._from_thing("team", slug)

    @classmethod
    def _from_thing(cls, thing, value):
        assert thing in ("id", "team")
        return cls.db.one("""

            SELECT packages.*::packages
              FROM packages
             WHERE {}=%s

        """.format(thing), (value,))

    @classmethod
    def insert(cls, owner, **fields):
        return cls.db.one("""
            INSERT INTO packages (package_manager, name, description, emails)
                 VALUES (%(package_manager)s, %(name)s, %(description)s, %(emails)s)
              RETURNING packages.*::packages

        """, fields)

    def set_team(self, team):
        """Set team for a package.
        """
        if not isinstance(team, Team):
            raise NotAllowed("Not a team!")
        elif team.is_closed:
            raise NotAllowed("team is closed")
        elif not team.is_approved:
            raise NotAllowed("team not approved")
        package_id = self.id
        slug = team.slug
        with self.db.get_cursor() as c:
            # TODO add event
            c.run("""
                UPDATE packages
                   SET team=%(slug)s
                 WHERE id=%(package_id)s
            """, locals())
        self.set_attributes(team=team)

    def set_payment_instruction(self, participant, amount):
        team_id = self.team_id
        if team_id:
            team = Team.from_id(team_id)
            participant.set_payment_instruction(team, amount)
        else:
            # TODO Add to pledges when we introduce it.
            pass


class NotAllowed(Exception):
    pass
