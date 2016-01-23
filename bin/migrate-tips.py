from gratipay.wireup import db, env
from gratipay.models.team import AlreadyMigrated

db = db(env())

teams = db.all("""
    SELECT distinct ON (t.slug) t.*::teams
      FROM teams t
      JOIN tips ON t.owner = tips.tippee    -- Only fetch teams whose owner have tips.
     WHERE t.is_approved IS TRUE            -- Only fetch approved teams.
       AND NOT EXISTS (                     -- Make sure not already migrated.
            SELECT 1
              FROM payment_instructions pi
             WHERE t.slug = pi.team
               AND pi.ctime < t.ctime
	     )
""")

for team in teams:
    try:
        ntips = team.migrate_tips()
        print("Migrated {} tip(s) for '{}'".format(ntips, team.slug))
    except AlreadyMigrated:
        print("'%s' already migrated." % team.slug)

print("Done.")
