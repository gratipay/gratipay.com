"""This is the code behind the ``sync-npm`` command line tool.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import sys
from threading import Lock


log_lock = Lock()

def log(*a, **kw):
    with log_lock:
        print(*a, file=sys.stderr, **kw)
