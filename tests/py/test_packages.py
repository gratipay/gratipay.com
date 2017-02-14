# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.models.package import NPM, Package
from gratipay.testing import Harness
from gratipay.testing.emails import EmailHarness


class TestPackage(Harness):

    def test_can_be_instantiated_from_id(self):
        p = self.make_package()
        assert Package.from_id(p.id).id == p.id

    def test_can_be_instantiated_from_names(self):
        self.make_package()
        assert Package.from_names(NPM, 'foo').name == 'foo'


class TestSendConfirmationEmail(EmailHarness):

    def test_sends_confirmation_email(self):
        p = self.make_package()
        p.send_confirmation_email('alice@example.com')
