#encoding: utf8
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing import BrowserHarness


class Tests(BrowserHarness):

    def trim(self, val):
        return self.js("window.Gratipay.trim('{}')".format(val))


    def test_trim_strips_all_unicode(self):
        assert self.trim('˚aø¶') == 'a'
        assert self.trim('封b') == 'b'

    def test_trim_strips_non_printable_ascii(self):
        assert self.trim('\\n\\t\\rc') == 'c'

    def test_trims_leading_and_trailing_whitespace(self):
        assert self.trim('  foo bar ') == 'foo bar'
        assert self.trim('  foo  bar ') == 'foo  bar'
