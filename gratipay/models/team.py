"""Teams on Gratipay receive payments and distribute payroll.
"""
import requests
from aspen import json, log
from gratipay.models import add_event
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
                         product_or_service, todo_url, onboarding_url,
                         owner)
                 VALUES (%(slug)s, %(slug_lower)s, %(name)s, %(homepage)s,
                         %(product_or_service)s, %(todo_url)s, %(onboarding_url)s,
                         %(owner)s)
              RETURNING teams.*::teams

        """, fields)


    def create_github_review_issue(self):
        """POST to GitHub, and return the URL of the new issue.
        """
        api_url = "https://api.github.com/repos/{}/issues".format(self.review_repo)
        data = json.dumps({ "title": self.name
                          , "body": "https://gratipay.com/{}/\n\n".format(self.slug) +
                                    "(This application will remain open for at least a week.)"
                           })
        out = ''
        try:
            r = requests.post(api_url, auth=self.review_auth, data=data)
            if r.status_code == 201:
                out = r.json()['html_url']
            else:
                log(r.status_code)
                log(r.text)
            err = str(r.status_code)
        except:
            err = "eep"
        if not out:
            out = "https://github.com/gratipay/team-review/issues#error-{}".format(err)
        return out


    def set_review_url(self, review_url):
        self.db.run("UPDATE teams SET review_url=%s WHERE id=%s", (review_url, self.id))
        self.set_attributes(review_url=review_url)


    def get_og_title(self):
        out = self.name
        receiving = self.receiving
        if receiving > 0:
            out += " receives $%.2f/wk" % receiving
        else:
            out += " is"
        return out + " on Gratipay"


    def update_receiving(self, cursor=None):
        r = (cursor or self.db).one("""
            WITH our_receiving AS (
                     SELECT amount
                       FROM current_payment_instructions
                       JOIN participants p ON p.username = participant
                      WHERE team = %(slug)s
                        AND p.is_suspicious IS NOT true
                        AND amount > 0
                        AND is_funded
                 )
            UPDATE teams t
               SET receiving = COALESCE((SELECT sum(amount) FROM our_receiving), 0)
                 , nreceiving_from = COALESCE((SELECT count(*) FROM our_receiving), 0)
                 , distributing = COALESCE((SELECT sum(amount) FROM our_receiving), 0)
                 , ndistributing_to = 1
             WHERE t.slug = %(slug)s
         RETURNING receiving, nreceiving_from, distributing, ndistributing_to
        """, dict(slug=self.slug))


        # This next step is easy for now since we don't have payroll.
        from gratipay.models.participant import Participant
        Participant.from_username(self.owner).update_taking()

        self.set_attributes( receiving=r.receiving
                           , nreceiving_from=r.nreceiving_from
                           , distributing=r.distributing
                           , ndistributing_to=r.ndistributing_to
                            )

    @property
    def status(self):
        return { None: 'unreviewed'
               , False: 'rejected'
               , True: 'approved'
                }[self.is_approved]

    def migrate_tips(self):
        payment_instructions = self.db.all("""
            SELECT pi.*
              FROM payment_instructions pi
              JOIN teams t ON t.slug = pi.team
              JOIN participants p ON t.owner = p.username
             WHERE p.username = %s
               AND pi.ctime < t.ctime
        """, (self.owner, ))

        # Make sure the migration hasn't been done already
        if payment_instructions:
            raise AlreadyMigrated

        return self.db.one("""
        WITH rows AS (

            INSERT INTO payment_instructions
                        (ctime, mtime, participant, team, amount, is_funded)
                 SELECT ct.ctime
                      , ct.mtime
                      , ct.tipper
                      , %(slug)s
                      , ct.amount
                      , ct.is_funded
                   FROM current_tips ct
                   JOIN participants p ON p.username = tipper
                  WHERE ct.tippee=%(owner)s
                    AND p.claimed_time IS NOT NULL
                    AND p.is_suspicious IS NOT TRUE
                    AND p.is_closed IS NOT TRUE
              RETURNING 1

        ) SELECT count(*) FROM rows;
        """, {'slug': self.slug, 'owner': self.owner})


    @property
    def image_url(self):
        return '/{}/image'.format(self.slug)

    def save_image(self, image, media_type):
        with self.db.get_cursor() as c:
            lobject = c.connection.lobject(self.image_oid, mode='wb')
            loid = lobject.oid
            c.run( "UPDATE teams SET image_oid=%s, image_type=%s WHERE id=%s"
                 , (loid, media_type, self.id)
                  )
            lobject.write(image)
            add_event(c, 'team', dict(action='upsert_image', oid=loid, id=self.id))
            self.set_attributes(image_oid=loid, image_type=media_type)
            return loid

    def load_image(self):
        image = None
        if self.image_oid != 0:
            with self.db.get_connection() as c:
                image = c.lobject(self.image_oid, mode='rb').read()
        return image


class AlreadyMigrated(Exception): pass
