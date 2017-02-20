"""Participants who received tips directly under Gittipay 1.0 will have their
tips migrated if and when they become the owner of a new Gratipay 2.0 team.
"""

from __future__ import absolute_import, division, print_function, unicode_literals


class TipMigration(object):
    """This mixin provides tip migration for teams.
    """

    def migrate_tips(self):
        """Migrate the Team owner's Gratipay 1.0 tips into 2.0 payment instructions to the Team.

        :return: ``None``
        :raises: :py:exc:`~gratipay.models.team.AlreadyMigrated` if payment
            instructions already exist for this Team

        This method gets called under :py:func:`migrate_all_tips` during payday.

        """
        payment_instructions = self.db.all("""
            SELECT pi.*
              FROM payment_instructions pi
              JOIN teams t ON t.id = pi.team_id
             WHERE t.owner = %s
               AND pi.ctime < t.ctime
        """, (self.owner, ))

        # Make sure the migration hasn't been done already
        if payment_instructions:
            raise AlreadyMigrated

        return self.db.one("""
        WITH rows AS (

            INSERT INTO payment_instructions
                        (ctime, mtime, participant_id, team_id, amount, is_funded)
                 SELECT ct.ctime
                      , ct.mtime
                      , (SELECT id FROM participants WHERE username=ct.tipper)
                      , %(team_id)s
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
        """, {'team_id': self.id, 'owner': self.owner})


def migrate_all_tips(db, print=print):
    """Migrate tips for all teams.

    :param GratipayDB db: a database object
    :param func print: a function that takes lines of log output
    :returns: ``None``

    This function loads :py:class:`~gratipay.models.team.Team` objects for all
    Teams where the owner had tips under Gratipay 1.0 but those tips have not
    yet been migrated into payment instructions under Gratipay 2.0. It then
    migrates the tips using :py:meth:`~gratipay.models.team.Team.migrate_tips`.

    This function is wrapped in a script, ``bin/migrate-tips.py``, which is
    `used during payday`_.

    .. _used during payday: http://inside.gratipay.com/howto/run-payday

    """
    teams = db.all("""
        SELECT distinct ON (t.id) t.*::teams
          FROM teams t
          JOIN tips ON t.owner = tips.tippee    -- Only fetch teams whose owners had tips under Gratipay 1.0
         WHERE t.is_approved IS TRUE            -- Only fetch approved teams
           AND NOT EXISTS (                     -- Make sure tips haven't been migrated for any teams with same owner
                SELECT 1
                  FROM payment_instructions pi
                  JOIN teams t2 ON t2.id = pi.team_id
                 WHERE t2.owner = t.owner
                   AND pi.ctime < t2.ctime
           )
    """)

    for team in teams:
        try:
            ntips = team.migrate_tips()
            print("Migrated {} tip(s) for '{}'".format(ntips, team.slug))
        except AlreadyMigrated:
            print("'%s' already migrated." % team.slug)

    print("Done.")


class AlreadyMigrated(Exception):
    """Raised by :py:meth:`~gratipay.models.team.migrate_tips`.
    """
