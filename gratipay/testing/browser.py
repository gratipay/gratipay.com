"""
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import atexit
import os
import time

from splinter.browser import _DRIVERS
from splinter.driver.webdriver import WebDriverElement
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.keys import Keys

from gratipay.security import user

from . import P
from .harness import Harness


# starting a browser is expensive, so we do so lazily, and once
_browser = None


class NeverLeft(Exception): pass
class NeverShowedUp(Exception): pass


# Monkey-patch .click to work around stackoverflow.com/q/11908249
def monkey_click(self):
    try:
        self._element.click()                   # Firefox 55
    except WebDriverException as exc:
        if not exc.msg.startswith('unknown error: Element is not clickable'):
            raise
        self._element.send_keys(Keys.RETURN)    # Chrome 60
WebDriverElement.click = monkey_click


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
        global _browser
        super(BrowserHarness, cls).setUpClass()
        if _browser is None:
            DriverClass = _DRIVERS[os.environ['WEBDRIVER_BROWSER']]
            _browser = DriverClass()
            atexit.register(_browser.quit)
        cls._browser = _browser

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

    def wait_to_disappear(self, selector, timeout=2):
        """Wait up to ``timeout`` seconds for element specified by ``selector``
        to disappear, returning ``None``.
        """
        end_time = time.time() + timeout
        while time.time() < end_time:
            if not self.has_element(selector):
                return
        raise NeverLeft(selector)

    def wait_for(self, selector, timeout=2):
        """Wait up to ``timeout`` seconds for element specified by ``selector``
        to appear, returning the element.
        """
        end_time = time.time() + timeout
        while time.time() < end_time:
            if self.has_element(selector):
                element = self.find_by_css(selector)
                if element.visible:
                    return element
        raise NeverShowedUp(selector)

    def wait_for_notification(self, type='notice', message=None, timeout=2):
        """Wait for a certain ``type`` of notification, with a certain message
        (if specified). Dismiss the notification and return the message.
        """
        notification_selector = '.notifications-fixed .notification-{}'.format(type)
        close_button_selector = 'span.btn-close'
        end_time = time.time() + timeout
        while time.time() < end_time:
            notification = self.wait_for(notification_selector, timeout).first
            candidate = notification.find_by_css('div').html
            if message is None or message == candidate:
                message = candidate
                break
        notification.find_by_css(close_button_selector).first.click()
        self.wait_to_disappear('#{} {}'.format(notification['id'], close_button_selector))
        return message

    def wait_for_success(self, message=None):
        """Wait for a success notification, with a certain message (if
        specified). Dismiss it and return the message.
        """
        return self.wait_for_notification('success', message)

    def wait_for_error(self, message=None):
        """Wait for an error notification, with a certain message (if
        specified). Dismiss it and return the message.
        """
        return self.wait_for_notification('error', message)

    def __getattr__(self, name):
        try:
            out = self.__getattribute__(name)
        except AttributeError:
            out = getattr(self._browser, name)
        return out
