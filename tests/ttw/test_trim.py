#encoding: utf8
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing import BrowserHarness


class Tests(BrowserHarness):

    def test_trim_strips_all_unicode(self):
        assert self.js("window.Gratipay.trim('˚aø¶')") == 'a'
        assert self.js("window.Gratipay.trim('封b')") == 'b'

    def test_trim_strips_non_printable_ascii(self):
        assert self.js("window.Gratipay.trim('\\n\\t\\rc')") == 'c'

    def test_trims_leading_and_trailing_whitespace(self):
        assert self.js("window.Gratipay.trim('  foo bar ')") == 'foo bar'
        assert self.js("window.Gratipay.trim('  foo  bar ')") == 'foo  bar'
