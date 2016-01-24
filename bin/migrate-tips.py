from gratipay.wireup import db, env
from gratipay.models.team import AlreadyMigrated

db = db(env())

teams = db.all("""
    SELECT distinct ON (t.slug) t.*::teams
      FROM teams t
      JOIN tips ON t.owner = tips.tippee    -- Only fetch teams whose owners had tips under Gratipay 1.0
     WHERE t.is_approved IS TRUE            -- Only fetch approved teams
       AND NOT EXISTS (                     -- Make sure tips haven't been migrated for any teams with same owner
            SELECT 1
              FROM payment_instructions pi
              JOIN teams t2 ON t2.slug = pi.team
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
