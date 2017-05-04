# -*- coding: utf-8 -*-
"""Define the top-level function for the ``sync-npm`` cli.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import time

from aspen import log

from gratipay import wireup
from gratipay.sync_npm import consume_change_stream, get_last_seq, production_change_stream
from gratipay.utils import sentry


def main():
    """This function is installed via an entrypoint in ``setup.py`` as
    ``sync-npm``.

    Usage::

      sync-npm

    """
    env = wireup.env()
    db = wireup.db(env)
    while 1:
        with sentry.teller(env):
            consume_change_stream(production_change_stream, db)
        try:
            last_seq = get_last_seq(db)
            sleep_for = 60
            log( 'Encountered an error, will pick up with %s in %s seconds (Ctrl-C to exit) ...'
               % (last_seq, sleep_for)
                )
            time.sleep(sleep_for)  # avoid a busy loop if thrashing
        except KeyboardInterrupt:
            return
