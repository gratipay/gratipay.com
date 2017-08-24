# -*- coding: utf-8 -*-
# Goofy name to avoid collision w/ ../py/test_security.py
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing import BrowserHarness
from selenium.common.exceptions import NoAlertPresentException


class RejectNullBytesInURI(BrowserHarness):

    def test_really_protects_against_reflected_xss(self):
        self.make_package()
        self.visit('/on/npm/foo')
        assert self.css('#banner h1').text == 'foo'
        # known bad in Chrome 60 and Firefox 55:
        self.visit('/on/npm/foo%2500bar%3Cx%3E%2500%2500%2500%2500%2500%2500%2500'
                   '%3Cscript%3Ealert(document.domain)%3C%2Fscript%3E')
        try:
            alert = self.get_alert()
        except NoAlertPresentException:
            assert 1
        else:
            alert.dismiss()  # avoid leaking into other tests
            assert 0, "Game over."
