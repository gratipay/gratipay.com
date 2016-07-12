from __future__ import absolute_import, division, print_function, unicode_literals

import atexit

from splinter.browser import _DRIVERS


def Browser(driver_name):
    # Override to clean up after ourselves properly.
    DriverClass = _DRIVERS[driver_name]
    driver = DriverClass()
    atexit.register(driver.quit)
    return driver
