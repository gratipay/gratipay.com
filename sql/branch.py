import sys

from gratipay import wireup
from gratipay.models.participant import Participant

db = wireup.db(wireup.env())

teams = db.all("""
    SELECT t.*::teams
      FROM teams t
""")

for team in teams:
    print("Updating team %s" % team.slug)
    Participant.from_username(team.owner).update_taking()

print("Done!")
