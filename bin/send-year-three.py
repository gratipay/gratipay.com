#!/usr/bin/env python
"""This is a one-off script to send emails for #3510.
"""
from __future__ import print_function

import random

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
       AND is_closed IS NOT TRUE
       AND is_suspicious IS NOT TRUE
       AND claimed_time IS NOT NULL
""")

N = len(participants)
print(N)
print([(p.username, p.email_address) for p in random.sample(participants, 5 if N > 5 else 1)])


# ----------------------------------------- SAFETY BELT ----------------------------------------- #
# ----------------------------------------- SAFETY BELT ----------------------------------------- #
# ----------------------------------------- SAFETY BELT ----------------------------------------- #
assert len(participants) == 1
assert participants[0].email_address == 'chad@zetaweb.com'
# ----------------------------------------- SAFETY BELT ----------------------------------------- #
# ----------------------------------------- SAFETY BELT ----------------------------------------- #
# ----------------------------------------- SAFETY BELT ----------------------------------------- #


# Send emails.
# ============

for p in participants:
    print("Queued for {} ({}={}).".format(p.email_address, p.username, p.id))
    p.queue_email('year_three', include_unsubscribe=False)

print("Sending {} email{} ...".format(N, '' if N == 1 else 's'))
nsent = Participant.dequeue_emails()
print("Sent {} email{}.".format(nsent, '' if nsent == 1 else 's'))
