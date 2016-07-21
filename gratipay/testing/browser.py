"""
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import atexit
import os
import time

from splinter.browser import _DRIVERS

from gratipay.security import user

from . import P
from .harness import Harness


def get_browser(driver_name):
    # Override to clean up after ourselves properly.
    DriverClass = _DRIVERS[driver_name]
    driver = DriverClass()
    atexit.register(driver.quit)
    return driver


class BrowserHarness(Harness):
    """This is a harness for through-the-web (TTW) testing. It passes
    everything through to an underlying `Splinter`_ browser, with the following
    exceptions:

    .. _Splinter: http://splinter.readthedocs.io/en/latest/

    """

    _browser = get_browser(os.environ['WEBDRIVER_BROWSER'])
    use_VCR = False  # without this we get fixture spam from communication with PhantomJS
    base_url = os.environ['WEBDRIVER_BASE_URL']

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

    def confirming(self, answer):
        """Return a context manager for working with confirm alerts cross-driver.
        """

        class Context(object):

            def __enter__(*a, **kw):
                if self._browser.driver_name == 'PhantomJS':
                    js_answer = 'true' if answer else 'false'
                    self.execute_script("window.__confirm__ = window.confirm");
                    self.execute_script("window.confirm = function(){ return %s; }" % js_answer);

            def __exit__(*a, **kw):
                if self._browser.driver_name == 'PhantomJS':
                    # Reset window.confirm, but gracefully adapt if we've reloaded the page.
                    self.execute_script("window.confirm = window.__confirm__ || window.confirm");
                else:
                    alert = self.get_alert()
                    if answer:
                        alert.accept()
                    else:
                        alert.dismiss()
                    time.sleep(0.2)

        return Context()

    def __getattr__(self, name):
        try:
            out = self.__getattribute__(name)
        except AttributeError:
            out = getattr(self._browser, name)
        return out

