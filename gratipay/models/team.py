"""Teams on Gratipay are plural participants with members.
"""
from postgres.orm import Model


class Team(Model):
    """Represent a Gratipay team.
    """

    typname = 'teams'

    def __eq__(self, other):
        if not isinstance(other, Team):
            return False
        return self.id == other.id

    def __ne__(self, other):
        if not isinstance(other, Team):
            return True
        return self.id != other.id


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
    def insert(cls, owner, **fields):
        fields['slug_lower'] = fields['slug'].lower()
        fields['owner'] = owner.username
        return cls.db.one("""

            INSERT INTO teams
                        (slug, slug_lower, name, homepage,
                         product_or_service, revenue_model, getting_involved, getting_paid,
                         owner)
                 VALUES (%(slug)s, %(slug_lower)s, %(name)s, %(homepage)s,
                         %(product_or_service)s, %(revenue_model)s, %(getting_involved)s,
                            %(getting_paid)s,
                         %(owner)s)
              RETURNING teams.*::teams

        """, fields)

    def get_og_title(self):
        out = self.name
        receiving = self.receiving
        if receiving > 0:
            out += " receives $%.2f/wk" % receiving
        else:
            out += " is"
        return out + " on Gratipay"


    def update_receiving(self, cursor=None):
        # Stubbed out for now. Migrate this over from Participant.
        pass


    @property
    def status(self):
        return { None: 'unreviewed'
               , False: 'rejected'
               , True: 'approved'
                }[self.is_approved]

    def migrate_tips(self):
        subscriptions = self.db.all("SELECT * FROM subscriptions WHERE team=%s", (self.slug,))

        # Make sure the migration hasn't been done already
        if subscriptions:
            raise AlreadyMigrated

        self.db.run("""

            INSERT INTO subscriptions
                        (ctime, mtime, subscriber, team, amount, is_funded)
                 SELECT ctime
                      , mtime
                      , tipper
                      , %(slug)s
                      , amount
                      , is_funded
                   FROM current_tips
                  WHERE tippee=%(owner)s

        """, {'slug': self.slug, 'owner': self.owner})

class AlreadyMigrated(Exception): pass
