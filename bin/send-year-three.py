#!/usr/bin/env python
"""This is a one-off script to resend emails for #3510.
"""
from gratipay.wireup import db, env


db = db(env())
participants = db.all("""
    SELECT p.*::participants
      FROM participants p
     WHERE email_address is not null
""")
assert len(participants) == 1

for p in participants:
    assert p.email_address == 'chad@zetaweb.com'
    p.queue_email('year_three')
