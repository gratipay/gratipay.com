"""This is the code behind the ``sync-npm`` command line tool, which keeps the
``packages`` table in our database in sync with npm. We run it on asynchronous
worker dynos at Heroku using the `Heroku scheduler`_. The top-level command is
at ``cli.main``, and the subcommands are in ``main`` in the other modules.

.. _Heroku scheduler: https://devcenter.heroku.com/articles/scheduler

"""
from __future__ import absolute_import, division, print_function, unicode_literals

import sys
from threading import Lock


log_lock = Lock()

def log(*a, **kw):
    """Log to stderr, thread-safely.
    """
    with log_lock:
        print(*a, file=sys.stderr, **kw)
