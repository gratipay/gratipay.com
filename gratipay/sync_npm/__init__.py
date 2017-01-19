"""This is the code behind the ``sync-npm`` command line tool, which keeps the
``packages`` table in our database in sync with npm. We run it on asynchronous
worker dynos at Heroku using the `Heroku scheduler`_. The top-level command is
at ``cli.main``, and the subcommands are in ``main`` in the other modules.

.. _Heroku scheduler: https://devcenter.heroku.com/articles/scheduler

"""
from __future__ import absolute_import, division, print_function, unicode_literals

import sys
from threading import Lock

from gratipay import wireup


log_lock = Lock()

def log(*a, **kw):
    """Log to stderr, thread-safely.
    """
    with log_lock:
        print(*a, file=sys.stderr, **kw)


class sentry(object):
    """This is a context manager to log to sentry. You have to pass in an ``Environment``
    object with a ``sentry_dsn`` attribute.
    """

    def __init__(self, env, noop=None):
        try:
            sys.stdout = sys.stderr  # work around aspen.log_dammit limitation; sigh
            self.tell_sentry = wireup.make_sentry_teller(env, noop)
        finally:
            sys.stdout = sys.__stdout__

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.tell_sentry(exc_type, {})
        return False
