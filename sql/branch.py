import sys

from gratipay import wireup

db = wireup.db(wireup.env())

participants = db.all("""
    SELECT p.*::participants
      FROM participants p
     WHERE (
        SELECT error
          FROM current_exchange_routes er
         WHERE er.participant = p.id
           AND network = 'braintree-cc'
     ) <> ''
""")

total = len(participants)

print("%s participants with failing cards" % total)

counter = 1

for p in participants:
    sys.stdout.write("\rUpdating (%i/%i)" % (counter, total))
    sys.stdout.flush()
    counter += 1

    p.update_giving_and_teams()

print("Done!")
