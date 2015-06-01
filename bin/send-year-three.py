#!/usr/bin/env python
"""This is a one-off script to send emails for #3510.
"""
from __future__ import print_function

from gratipay.models.participant import Participant
from gratipay.wireup import db, env

def noop(*a, **kw): pass
Participant._tell_sentry = noop


# Fetch participants.
# ===================

db = db(env())
participants = db.all("""
    SELECT p.*::participants
      FROM participants p
     WHERE email_address is not null
""")

assert len(participants) == 1
assert participants[0].email_address == 'chad@zetaweb.com'


# Send emails.
# ============

for p in participants:
    p.queue_email('year_three')

nsent = Participant.dequeue_emails()
print("Sent %s email%s".format(nsent, '' if nsent == 1 else 's'))
