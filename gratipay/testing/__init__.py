"""Helpers for testing Gratipay.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

from decimal import Decimal

import pytest
from aspen import log_dammit

from ..models.participant import Participant
from ..models.team import Team
from ..utils import markdown

D = Decimal                     #:
P = Participant.from_username   #:
T = Team.from_slug              #:

from .harness import Harness
from .billing import BillingHarness
from .browser import BrowserHarness

__all__ = ['Harness', 'BillingHarness', 'BrowserHarness', 'D','P','T']


class Foobar(Exception): pass


def debug_http():
    """Turns on debug logging for HTTP traffic. Happily, this includes VCR usage.

    http://stackoverflow.com/a/16630836

    """
    import logging

    # These two lines enable debugging at httplib level
    # (requests->urllib3->http.client) You will see the REQUEST, including
    # HEADERS and DATA, and RESPONSE with HEADERS but without DATA.  The
    # only thing missing will be the response.body which is not logged.
    try:
        import http.client as http_client
    except ImportError:
        # Python 2
        import httplib as http_client
    http_client.HTTPConnection.debuglevel = 1

    # You must initialize logging, otherwise you'll not see debug output.
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True


# Provide a decorator to skip tests when marky-markdown is missing.

try:
    markdown.render_like_npm('test')
except OSError as exc:
    MISSING_MARKY_MARKDOWN = True
    log_dammit('Will skip marky-markdown-related tests because:', exc.args[0])
else:
    MISSING_MARKY_MARKDOWN = False

def skipif_missing_marky_markdown(func):
    return pytest.mark.skipif(MISSING_MARKY_MARKDOWN, reason="missing marky-markdown")(func)
