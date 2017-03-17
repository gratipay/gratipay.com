# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import sys

from gratipay.application import Application


def main(_argv=sys.argv, _input=raw_input):
    """This is a script to flush the email queue.

    In production we have a thread inside the main web process that sends
    emails according to the FLUSH_EMAIL_QUEUE_EVERY envvar. This script is more
    for development, though when we're ready to move to a separate worker
    process/dyno we can start with this.

    """
    Application().email_queue.flush()
