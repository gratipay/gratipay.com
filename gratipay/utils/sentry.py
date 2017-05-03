# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import sys
import traceback

from aspen import log
from gratipay import wireup


log_to_console = lambda exc_type, state: log(traceback.format_exc())


class teller(object):
    """This is a context manager to log to Sentry. You have to pass in an
    ``Environment`` object with a ``sentry_dsn`` attribute.
    """

    def __init__(self, env, fallback=log_to_console):
        try:
            sys.stdout = sys.stderr  # work around aspen.log_dammit limitation; sigh
            self.tell_sentry = wireup.make_sentry_teller(env, fallback)
        finally:
            sys.stdout = sys.__stdout__

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.tell_sentry(exc_type, {})
        return True
