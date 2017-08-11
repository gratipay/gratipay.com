# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import mock
from gratipay.models.package import Package, NPM
from gratipay.models.package.emails import PRIMARY, VERIFIED, UNVERIFIED, UNLINKED, OTHER
from gratipay.testing import Harness
from psycopg2 import IntegrityError
from pytest import raises


Foo = lambda cursor=None: Package.from_names(NPM, 'foo', cursor)


class Basics(Harness):

    def test_can_be_instantiated_from_id(self):
        package = self.make_package()
        assert Package.from_id(package.id).id == package.id

    def test_from_id_can_use_a_cursor(self):
        package = self.make_package()
        with self.db.get_cursor() as cursor:
            assert Package.from_id(package.id, cursor).id == package.id

    def test_can_be_instantiated_from_names(self):
        self.make_package()
        assert Package.from_names(NPM, 'foo').name == 'foo'

    def test_from_names_can_use_a_cursor(self):
        self.make_package()
        with self.db.get_cursor() as cursor:
            assert Package.from_names(NPM, 'foo', cursor).name == 'foo'


    def test_can_be_inserted_via_upsert(self):
        Package.upsert(NPM, name='foo', description='Foo!', emails=[])
        assert Foo().name == 'foo'

    def test_can_be_updated_via_upsert(self):
        self.make_package()
        Package.upsert(NPM, name='foo', description='Bar!', emails=[])
        assert Foo().description == 'Bar!'

    def test_can_be_upserted_in_a_transaction(self):
        self.make_package(description='Before')
        with self.db.get_cursor() as cursor:
            Package.upsert(NPM, name='foo', description='After', emails=[], cursor=cursor)
            assert Foo().description == 'Before'
        assert Foo().description == 'After'


    def test_can_be_deleted(self):
        self.make_package().delete()
        assert Foo() is None

    def test_can_be_deleted_in_a_transaction(self):
        package = self.make_package()
        with self.db.get_cursor() as cursor:
            package.delete(cursor)
            assert Foo() == package
        assert Foo() is None


class Linking(Harness):

    def link(self, package_name='foo'):
        alice = self.make_participant('alice')
        package = self.make_package(name=package_name)
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

    def test_linking_team_ignores_scope(self):
        _, _, team = self.link(package_name='@foo/bar')
        assert team.slug == 'bar'

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

    def test_deleting_package_leaves_team_unlinked(self):
        _, package, team = self.link()
        assert team.package is not None
        package.delete()
        assert team.package is None


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


class GetPackagesForClaiming(Harness):

    def test_gets_packages_for_claiming(self):
        foo = self.make_package()
        alice = self.make_participant('alice', email_address='alice@example.com')
        assert alice.get_packages_for_claiming(NPM) == [(foo, None, True, 'alice@example.com')]

    def test_excludes_packages_for_half_verified_emails(self):
        foo = self.make_package()
        alice = self.make_participant('alice', email_address='alice@example.com')
        self.make_package(name='bar', emails=['bob@example.com'])
        alice.start_email_verification('bob@example.com')
        assert alice.get_packages_for_claiming(NPM) == [(foo, None, True, 'alice@example.com')]

    def test_includes_packages_for_verified_but_non_primary_emails(self):
        foo = self.make_package()
        alice = self.make_participant('alice', email_address='alice@example.com')
        bar = self.make_package(name='bar', emails=['bob@example.com'])
        self.add_and_verify_email(alice, 'bob@example.com')
        assert alice.get_packages_for_claiming(NPM) == \
                    [(foo, None, True, 'alice@example.com'), (bar, None, False, 'bob@example.com')]

    def test_matches_primary_email(self):
        foo = self.make_package(emails=['alice@example.com', 'bob@example.com', 'cat@example.com'])
        alice = self.make_participant('alice', email_address='cat@example.com')
        self.add_and_verify_email(alice, 'bob@example.com')
        self.add_and_verify_email(alice, 'alice@example.com')
        assert alice.get_packages_for_claiming(NPM) == [(foo, None, True, 'cat@example.com')]

    def test_matches_non_primary_verified_email(self):
        foo = self.make_package(emails=['bob@example.com', 'cat@example.com'])
        alice = self.make_participant('alice', email_address='alice@example.com')
        self.add_and_verify_email(alice, 'cat@example.com')
        self.add_and_verify_email(alice, 'bob@example.com')
        assert alice.get_packages_for_claiming(NPM) == [(foo, None, False, 'bob@example.com')]

    def test_includes_packages_already_claimed_by_self(self):
        foo = self.make_package()
        alice = self.make_participant('alice', email_address='alice@example.com')
        foo.get_or_create_linked_team(self.db, alice)
        assert alice.get_packages_for_claiming(NPM) == [(foo, alice, True, 'alice@example.com')]

    def test_includes_packages_already_claimed_by_other(self):
        foo = self.make_package(emails=['alice@example.com', 'bob@example.com'])
        alice = self.make_participant('alice', email_address='alice@example.com')
        foo.get_or_create_linked_team(self.db, alice)
        bob = self.make_participant('bob', email_address='bob@example.com')
        assert bob.get_packages_for_claiming(NPM) == [(foo, alice, True, 'bob@example.com')]
