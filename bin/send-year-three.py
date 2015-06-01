#!/usr/bin/env python

"""This is a one-off script to resend emails for #3355."""

import sys

from gratipay import wireup

env = wireup.env()
db = wireup.db(env)

# Temporary, will fill with actual values when running script
email_txt = """
    rohitpaulk@live.com
    abcd@gmail.com
"""

emails = [email.strip() for email in email_txt.split()]

assert len(emails) == 176

participants = []

participants = db.all("""
    SELECT p.*::participants
      FROM participants p
     WHERE email_address IN %s
""", (tuple(emails), ))

for p in participants:
    p.queue_email('double_emails')

print("Done")
sys.exit()
