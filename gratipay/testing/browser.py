"""
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import atexit
import os

from splinter.browser import _DRIVERS

from gratipay.security import user

from . import P
from .harness import Harness


class BrowserHarness(Harness):
    """This is a harness for through-the-web (TTW) testing. It passes
    everything through to an underlying `Splinter`_ browser, with the following
    exceptions:

    .. _Splinter: http://splinter.readthedocs.io/en/latest/

    """

    _browser = None
    use_VCR = False  # without this we get fixture spam from communication with PhantomJS
    base_url = os.environ['WEBDRIVER_BASE_URL']

    @classmethod
    def setUpClass(cls):
        super(BrowserHarness, cls).setUpClass()

        # starting a browser is expensive, so we do so lazily, and once
        if cls._browser is None:
            DriverClass = _DRIVERS[os.environ['WEBDRIVER_BROWSER']]
            cls._browser = DriverClass()
            atexit.register(cls._browser.quit)

    def setUp(self):
        Harness.setUp(self)
        self.cookies.delete()
        self.visit('/')

    def tearDown(self):
        Harness.tearDown(self)
        self.cookies.delete()

    def visit(self, url):
        """Extend to prefix our base URL.
        """
        return self._browser.visit(self.base_url + url)

    def sign_in(self, username):
        """Given a username, sign in the user.
        """
        if self.url == 'about:blank':
            # We need a page loaded in order to set an authentication cookie.
            self.visit('/')
        # This is duplicated from User.sign_in to work with Splinter's cookie API.
        token = user.uuid.uuid4().hex
        expires = user.utcnow() + user.SESSION_TIMEOUT
        P(username).update_session(token, expires)
        self.cookies.add({user.SESSION: token})

    def css(self, selector):
        """Shortcut for find_by_css.
        """
        return self.find_by_css(selector)

    def js(self, code):
        """Shortcut for evaluate_script.
        """
        return self.evaluate_script(code)

    def has_text(self, text, timeout=None):
        """Shortcut for is_text_present.
        """
        return self.is_text_present(text, timeout)

    def has_element(self, selector, timeout=None):
        """Shortcut for is_element_present_by_css.
        """
        return self.is_element_present_by_css(selector, timeout)

    def __getattr__(self, name):
        try:
            out = self.__getattribute__(name)
        except AttributeError:
            out = getattr(self._browser, name)
        return out

