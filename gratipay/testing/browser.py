from __future__ import absolute_import, division, print_function, unicode_literals

import atexit
import os

from gratipay.models.participant import Participant
from gratipay.security import user
from splinter.browser import _DRIVERS


def Browser(driver_name):
    DriverClass = _DRIVERS[driver_name]

    # Monkey-patch to use a configurable base URL
    base_url = os.environ['WEBDRIVER_BASE_URL']
    def visit(self, url):
        return super(DriverClass, self).visit(base_url + url)
    DriverClass.visit = visit

    # Monkey-patch to support authentication
    def sign_in(self, username):
        if self.url == 'about:blank':
            # We need a page loaded in order to set an authentication cookie.
            self.visit('/')
        # This is duplicated from User.sign_in to work with Splinter's cookie API.
        token = user.uuid.uuid4().hex
        expires = user.utcnow() + user.SESSION_TIMEOUT
        Participant.from_username(username).update_session(token, expires)
        self.cookies.add({user.SESSION: token})
    DriverClass.sign_in = sign_in

    driver = DriverClass()
    atexit.register(driver.quit)
    return driver
