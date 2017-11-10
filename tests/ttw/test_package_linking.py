# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing import BrowserHarness


class Test(BrowserHarness):

    def test_package_owner_prompted_to_contact_support(self):
        self.make_package(claimed_by='alice')
        #admin = self.make_participant('admin', is_admin=True)
        self.sign_in('alice')
        self.visit('/foo/settings/')
        import pdb; pdb.set_trace()

