# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import sys

from gratipay import wireup
from gratipay.models.participant import Participant


def main(_argv=sys.argv, _input=raw_input):
    """This is a script to dequeue and send emails.

    In production we have a thread inside the main web process that dequeues
    emails according to the DEQUEUE_EMAILS_EVERY envvar. This script is more
    for development, though when we're ready to move to a separate worker
    process/dyno we can start with this.

    """
    env = wireup.env()
    wireup.make_sentry_teller(env)
    wireup.mail(env)
    wireup.db(env)
    Participant.dequeue_emails()
