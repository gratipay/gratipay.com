"""Teams on Gratipay receive payments and distribute payouts.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import re
from decimal import Decimal

import requests
from aspen import json, log
from gratipay.billing.exchanges import MINIMUM_CHARGE
from gratipay.exceptions import InvalidTeamName
from gratipay.models import add_event
from gratipay.models.team import mixins
from postgres.orm import Model


# Should have at least one letter.
TEAM_NAME_PATTERN = re.compile(r'^(?=.*[A-Za-z])([A-Za-z0-9.,-_ ]+)$')


def slugize(name):
    """ Create a slug from a team name.
    """
    if TEAM_NAME_PATTERN.match(name) is None:
      raise InvalidTeamName

    slug = name.strip()
    for c in (',', ' '):
        slug = slug.replace(c, '-') # Avoid % encoded characters in slug url.
    while '--' in slug:
        slug = slug.replace('--', '-')
    slug = slug.strip('-')
    return slug


class Team(Model, mixins.Available, mixins.Membership, mixins.Takes, mixins.TipMigration):
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


    # Computed Values
    # ===============

    #: The total amount of money this team receives during payday. Read-only;
    #: modified by
    #: :py:meth:`~gratipay.models.participant.Participant.set_payment_instruction`.

    receiving = 0


    #: The number of participants that are giving to this team. Read-only;
    #: modified by
    #: :py:meth:`~gratipay.models.participant.Participant.set_payment_instruction`.

    nreceiving_from = 0


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
                         product_or_service, owner)
                 VALUES (%(slug)s, %(slug_lower)s, %(name)s, %(homepage)s,
                         %(product_or_service)s, %(owner)s)
              RETURNING teams.*::teams

        """, fields)

    def get_payment_distribution(self):
        """Returns a data structure in the form of::

            [
                [PAYMENT1, PAYMENT2...PAYMENTN],
                nreceiving_from,
                total_amount_received
            ]

        where each ``PAYMENTN`` is in the form::

            [
                amount,
                number_of_tippers_for_this_amount,
                total_amount_given_at_this_amount,
                proportion_of_payments_at_this_amount,
                proportion_of_total_amount_at_this_amount
            ]

        """
        SQL = """
            SELECT amount
                 , count(amount) AS nreceiving_from
              FROM ( SELECT DISTINCT ON (participant_id)
                            amount
                          , participant_id
                       FROM payment_instructions
                       JOIN participants p ON p.id = participant_id
                      WHERE team_id=%s
                        AND is_funded
                        AND p.is_suspicious IS NOT true
                   ORDER BY participant_id
                          , mtime DESC
                    ) AS foo
             WHERE amount > 0
          GROUP BY amount
          ORDER BY amount
        """

        tip_amounts = []

        npatrons = 0.0  # float to trigger float division
        total_amount = Decimal('0.00')
        for rec in self.db.all(SQL, (self.id,)):
            tip_amounts.append([ rec.amount
                               , rec.nreceiving_from
                               , rec.amount * rec.nreceiving_from
                                ])
            total_amount += tip_amounts[-1][2]
            npatrons += rec.nreceiving_from

        for row in tip_amounts:
            row.append((row[1] / npatrons) if npatrons > 0 else 0)
            row.append((row[2] / total_amount) if total_amount > 0 else 0)

        return tip_amounts, npatrons, total_amount


    def update(self, **kw):
      updateable = frozenset(['name', 'product_or_service', 'homepage',
                              'onboarding_url'])

      cols, vals = zip(*kw.items())
      assert set(cols).issubset(updateable)

      old_value = {}
      for col in cols:
        old_value[col] = getattr(self, col)

      cols = ', '.join(cols)
      placeholders = ', '.join(['%s']*len(vals))

      with self.db.get_cursor() as c:
        c.run("""
          UPDATE teams
             SET ({0}) = ({1})
           WHERE id = %s
          """.format(cols, placeholders), vals+(self.id,)
        )
        add_event(c, 'team', dict( action='update'
                                 , id=self.id
                                 , **old_value
                                  ))
        self.set_attributes(**kw)


    def get_dues(self):
        rec = self.db.one("""
            WITH our_cpi AS (
                SELECT due, is_funded
                  FROM current_payment_instructions cpi
                 WHERE team_id=%(team_id)s
            )
            SELECT (
                    SELECT COALESCE(SUM(due), 0)
                      FROM our_cpi
                     WHERE is_funded
                   ) AS funded
                 , (
                    SELECT COALESCE(SUM(due), 0)
                      FROM our_cpi
                     WHERE NOT is_funded
                   ) AS unfunded
        """, {'team_id': self.id})

        return rec.funded, rec.unfunded


    def get_upcoming_payment(self):
        return self.db.one("""
            SELECT COALESCE(SUM(amount + due), 0)
              FROM current_payment_instructions cpi
              JOIN participants p ON cpi.participant_id = p.id
             WHERE team_id = %(team_id)s
               AND is_funded                -- Check whether the payment is funded
               AND (                        -- Check whether the user will hit the minimum charge
                    SELECT SUM(amount + due)
                      FROM current_payment_instructions cpi2
                     WHERE cpi2.participant_id = p.id
                       AND cpi2.is_funded
                   ) >= %(mcharge)s
        """, {'team_id': self.id, 'mcharge': MINIMUM_CHARGE})


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
                       JOIN participants p ON p.id = participant_id
                      WHERE team_id = %(team_id)s
                        AND p.is_suspicious IS NOT true
                        AND amount > 0
                        AND is_funded
                 )
            UPDATE teams t
               SET receiving = COALESCE((SELECT sum(amount) FROM our_receiving), 0)
                 , nreceiving_from = COALESCE((SELECT count(*) FROM our_receiving), 0)
                 , distributing = COALESCE((SELECT sum(amount) FROM our_receiving), 0)
                 , ndistributing_to = 1
             WHERE t.id = %(team_id)s
         RETURNING receiving, nreceiving_from, distributing, ndistributing_to
        """, dict(team_id=self.id))


        # This next step is easy for now since we don't have payouts.
        from gratipay.models.participant import Participant
        Participant.from_username(self.owner).update_taking(cursor or self.db)

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

    def to_dict(self):
        return {
            'homepage': self.homepage,
            'name': self.name,
            'nreceiving_from': self.nreceiving_from,
            'onboarding_url': self.onboarding_url,
            'owner': '~' + self.owner,
            'receiving': self.receiving,
            'slug': self.slug,
            'status': self.status
        }


    # Images
    # ======

    IMAGE_SIZES = ('original', 'large', 'small')

    def get_image_url(self, size):
        assert size in ('original', 'large', 'small'), size
        return '/{}/image?size={}'.format(self.slug, size)

    def save_image(self, original, large, small, image_type):
        with self.db.get_cursor() as c:
            oids = {}
            for size in self.IMAGE_SIZES:
                lobject = c.connection.lobject(getattr(self, 'image_oid_'+size), mode='wb')
                lobject.write(locals()[size])
                oids[size] = lobject.oid
                lobject.close()

            c.run("""UPDATE teams
                        SET image_oid_original=%s, image_oid_large=%s, image_oid_small=%s
                          , image_type=%s
                      WHERE id=%s"""
                 , (oids['original'], oids['large'], oids['small'], image_type, self.id)
                  )
            add_event(c, 'team', dict( action='upsert_image'
                                     , id=self.id
                                     , **oids
                                      ))
            self.set_attributes( image_type=image_type
                               , **{'image_oid_'+size: oids[size] for size in oids}
                                )
            return oids

    def load_image(self, size):
        assert size in self.IMAGE_SIZES, size
        image = None
        oid = getattr(self, 'image_oid_{}'.format(size))
        if oid != 0:
            with self.db.get_connection() as c:
                image = c.lobject(oid, mode='rb').read()
        return image
