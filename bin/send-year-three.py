#!/usr/bin/env python
"""This is a one-off script to send emails for #3510.
"""
from __future__ import print_function

import sys
class DevNull:
    def write(*a): pass
    def flush(*a): pass
sys.stdout = DevNull()
from gratipay.main import Participant, db
sys.stdout = sys.__stdout__


# Fetch participants.
# ===================

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
    p.queue_email('year_three', include_unsubscribe=False)

nsent = Participant.dequeue_emails()
print("Sent {} email{}.".format(nsent, '' if nsent == 1 else 's'))
