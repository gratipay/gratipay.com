# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import mock
from gratipay.models.package import Package, NPM
from gratipay.models.package.emails import PRIMARY, VERIFIED, UNVERIFIED, UNLINKED, OTHER
from gratipay.testing import Harness
from psycopg2 import IntegrityError
from pytest import raises


class TestPackage(Harness):

    def test_can_be_instantiated_from_id(self):
        p = self.make_package()
        assert Package.from_id(p.id).id == p.id

    def test_can_be_instantiated_from_names(self):
        self.make_package()
        assert Package.from_names(NPM, 'foo').name == 'foo'


class Linking(Harness):

    def link(self):
        alice = self.make_participant('alice')
        package = self.make_package()
        with self.db.get_cursor() as c:
            team = package.get_or_create_linked_team(c, alice)
        return alice, package, team

    def test_package_team_is_none(self):
        assert self.make_package().team is None

    def test_team_package_is_none(self):
        assert self.make_team().package is None

    def test_can_link_to_a_new_team(self):
        _, package, team = self.link()
        assert team.package == package
        assert package.team == team

    def test_linking_is_idempotent(self):
        alice, package, team = self.link()
        for i in range(5):
            with self.db.get_cursor() as c:
                assert package.get_or_create_linked_team(c, alice) == team

    def test_team_can_only_be_linked_from_one_package(self):
        _ , _, team = self.link()
        bar = self.make_package(name='bar')
        raises( IntegrityError
              , self.db.run
              , 'INSERT INTO teams_to_packages (team_id, package_id) VALUES (%s, %s)'
              , (team.id, bar.id)
               )

    def test_package_can_only_be_linked_from_one_team(self):
        _, package, _ = self.link()
        bar = self.make_team(name='Bar')
        raises( IntegrityError
              , self.db.run
              , 'INSERT INTO teams_to_packages (team_id, package_id) VALUES (%s, %s)'
              , (bar.id, package.id)
               )

    def test_linked_team_takes_package_name(self):
        _, _, team = self.link()
        assert team.slug == 'foo'

    def test_linking_team_tries_other_names(self):
        self.make_team(name='foo')
        _, _, team = self.link()
        assert team.slug == 'foo-1'

    @mock.patch('gratipay.models.package.team.uuid')
    def test_linking_team_drops_back_to_uuid4_eventually(self, uuid):
        uuid.uuid4.return_value.hex = 'deadbeef-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
        self.make_team(name='foo')                  # take `foo`
        for i in range(1, 10):
            self.make_team(name='foo-{}'.format(i)) # take `foo-{1-9}`
        _, _, team = self.link()
        assert team.slug == 'deadbeef-aaaa-aaaa-aaaa-aaaaaaaaaaaa'

    def test_linked_team_takes_package_description(self):
        _, _, team = self.link()
        assert team.product_or_service == 'Foo fooingly.'

    def test_linked_team_has_remote_package_url_as_homepage(self):
        _, _, team = self.link()
        assert team.homepage == 'https://www.npmjs.com/package/foo'

    def test_review_url_doesnt_get_set_here(self):
        _, _, team = self.link()
        assert team.review_url is None

    def test_closing_team_unlinks_package(self):
        _, _, team = self.link()
        team.close()
        assert Package.from_names('npm', 'foo').team is None


class GroupEmailsForParticipant(Harness):

    def test_ordering(self):
        emails = ['amail', 'bmail', 'cmail', 'dmail', 'email', 'lumail', 'primary']
        foo = self.make_package(emails=emails)

        # verified for other
        bob = self.make_participant('bob', claimed_time='now')
        bob.start_email_verification('bmail')
        nonce = bob.get_email('bmail').nonce
        bob.finish_email_verification('bmail', nonce)

        # linked to other but unverified
        bob.start_email_verification('dmail')

        # primary
        alice = self.make_participant('alice', claimed_time='now')
        alice.start_email_verification('primary')
        nonce = alice.get_email('primary').nonce
        alice.finish_email_verification('primary', nonce)

        # linked to self but unverified
        alice.start_email_verification('lumail')

        # verified for self
        alice.start_email_verification('amail')
        nonce = alice.get_email('amail').nonce
        alice.finish_email_verification('amail', nonce)

        # unlinked
        pass  # cmail, email -- tests alphabetization within grouping

        # creation order doesn't relate to final order
        emails = foo.classify_emails_for_participant(alice)
        assert emails == [ ('primary', PRIMARY)
                         , ('amail', VERIFIED)
                         , ('lumail', UNVERIFIED)
                         , ('cmail', UNLINKED)
                         , ('dmail', UNLINKED)
                         , ('email', UNLINKED)
                         , ('bmail', OTHER)
                          ]
