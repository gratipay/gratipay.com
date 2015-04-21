from gratipay import wireup

env = wireup.env()
db = wireup.db(env)

participants = []

with open('./sql/emails.txt') as f:
    emails = [line.rstrip() for line in f]
    participants = db.all("""
        SELECT p.*::participants
          FROM participants p
         WHERE email_address IN %s
    """, (tuple(emails), ))

for p in participants:
    p.queue_email('double_emails')
