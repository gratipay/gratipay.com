# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import sys

from gratipay import wireup
from gratipay.models.participant import Participant


def main(_argv=sys.argv, _input=raw_input):
    """This is a script to dequeue and send emails.
    """
    env = wireup.env()
    wireup.make_sentry_teller(env)
    wireup.mail(env)
    wireup.db(env)
    Participant.dequeue_emails()
