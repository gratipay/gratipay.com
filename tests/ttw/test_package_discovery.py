# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing import BrowserHarness


class Tests(BrowserHarness):

    def assertDiscovery(self):
        instructions = self.css('.instructions').text
        assert instructions == 'Paste a package.json to find packages to pay for:'

    def test_anon_gets_discovery_page_by_default(self):
        self.visit('/on/npm/')
        self.assertDiscovery()

    def test_auth_also_gets_discovery_page_by_default(self):
        self.make_participant('alice')
        self.sign_in('alice')
        self.visit('/on/npm/')
        self.assertDiscovery()

    def test_pasting_a_package_json_works(self):
        self.make_package(name='amperize', description='Amperize!')
        mysql = self.make_package(name='mysql', description='MySQL!', emails=['bob@example.com'])
        self.make_package(name='netjet', description='Netjet!', emails=['cat@example.com'])
        scape = self.make_package(name='scape', description='Reject!', emails=['goat@example.com'])
        self.claim_package(self.make_participant('alice'), 'amperize')
        self.claim_package(self.make_participant('bob'), 'mysql')
        self.claim_package(self.make_participant('goat'), 'scape')

        admin = self.make_admin()
        mysql.team.update(name='MySQL')
        mysql.team.update_review_status('approved', admin)
        scape.team.update_review_status('rejected', admin)

        self.visit('/on/npm/')
        self.css('textarea').fill('''\

            { "dependencies": {"scape": "...", "mysql": "...", "amperize": "..."}
            , "optionalDependencies": {"netjet": "...", "falafel": "..."}
             }

        ''')
        self.css('form.package-json button').click()

        names = [x.text for x in self.css('.listing-name')]
        assert names == ['MySQL (mysql on npm)', 'scape', 'amperize', 'netjet', 'falafel']

        statuses = [x.text[3:] for x in self.css('.listing-details .status')]
        assert statuses == ['Approved', 'Rejected', 'Unreviewed', 'Unclaimed']

        enabled = [not x.has_class('disabled') for x in self.css('td.item')]
        assert enabled == [True, True, True, True, False]

        assert [x.text for x in self.css('.listing-details .i')] == ['1', '2', '3', '4', '5']
