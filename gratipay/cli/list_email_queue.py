# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import sys

from gratipay import wireup


QUEUE = """\
    SELECT p.id, spt_name, p.username, p.email_address
      FROM email_queue eq
      JOIN participants p
        ON eq.participant = p.id
  ORDER BY eq.id ASC
"""


def main(_argv=sys.argv, _print=print):
    """This is a script to list the email queue.
    """
    env = wireup.env()

    db = wireup.db(env)
    for i, email in enumerate(db.all(QUEUE), start=1):
        _print("{:>4} {:>6} {:<16} {:<24} {}".format(i, *email))

    # Trigger logging of sentry/mailer configuration for reference.
    wireup.make_sentry_teller(env)
    wireup.mail(env)
