from gratipay.wireup import db, env
from gratipay.models.team import Team, AlreadyMigrated

db = db(env())

slugs = db.all("""
    SELECT slug
      FROM teams
     WHERE is_approved IS TRUE
""")

for slug in slugs:
    team = Team.from_slug(slug)
    try:
        ntips = team.migrate_tips()
        print("Migrated {} tip(s) for '{}'".format(ntips, slug))
    except AlreadyMigrated:
        print("'%s' already migrated." % slug)

print("Done.")
