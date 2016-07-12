from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing import BrowserHarness


class Tests(BrowserHarness):

    def setUp(self):
        BrowserHarness.setUp(self)

        # Since console will already exist, we'll need to clear it
        # before calling `mock_console()`

        self.execute_script("""
            window.console = null;
            mock_console();
        """)

    def test_nuking_console_nukes_console(self):
        self.execute_script("window.console = null;")
        assert self.js("window.console === null")

    def test_console_is_not_null(self):
        assert self.js("window.console !== null")

    def test_console_has_the_right_attributes(self):
        expected = ['log', 'debug', 'info', 'warn', 'error', 'assert', 'dir', 'dirxml', 'group',
                    'groupEnd', 'time', 'timeEnd', 'count', 'trace', 'profile', 'profileEnd']
        assert self.js("Object.keys(window.console)") == expected
