"""Teams on Gratipay are plural participants with members.
"""
from postgres.orm import Model


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


    def update_receiving(self, cursor=None):
        # Stubbed out for now. Migrate this over from Participant.
        pass
