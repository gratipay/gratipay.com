from gratipay import wireup

db = wireup.db(wireup.env())

participants = db.all("""
    SELECT p.*::participants
      FROM participants p
      JOIN payment_instructions pi ON pi.participant = p.username -- Only include those with tips
""")
total = len(participants)
counter = 0

for p in participants:
    print("Participant %s/%s" % (counter, total))
    p.update_giving_and_teams()
    counter += 1
