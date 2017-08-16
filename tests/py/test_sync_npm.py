# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing import Harness

from gratipay import sync_npm


class ProcessDocTests(Harness):

    def test_returns_None_if_no_name(self):
        assert sync_npm.process_doc({}) is None

    def test_backfills_missing_keys(self):
        actual = sync_npm.process_doc({'name': 'foo'})
        assert actual == {'name': 'foo', 'description': '', 'emails': []}

    def test_extracts_maintainer_emails(self):
        doc = {'name': 'foo', 'maintainers': [{'email': 'alice@example.com'}]}
        assert sync_npm.process_doc(doc)['emails'] == ['alice@example.com']

    def test_skips_empty_emails(self):
        doc = {'name': 'foo', 'maintainers': [{'email': ''}, {'email': '     '}]}
        assert sync_npm.process_doc(doc)['emails'] == []

    def test_sorts_emails(self):
        doc = {'name': 'foo', 'maintainers': [{'email': 'bob'}, {'email': 'alice'}]}
        assert sync_npm.process_doc(doc)['emails'] == ['alice', 'bob']

    def test_dedupes_emails(self):
        doc = {'name': 'foo', 'maintainers': [{'email': 'alice'}, {'email': 'alice'}]}
        assert sync_npm.process_doc(doc)['emails'] == ['alice']


class ConsumeChangeStreamTests(Harness):

    def change_stream(self, changes):
        for i, change in enumerate(changes):
            change['seq'] = i
            yield change

    def test_packages_starts_empty(self):
        assert self.db.all('select * from packages') == []


    def test_consumes_change_stream(self):
        docs = [ {'doc': {'name': 'foo', 'description': 'Foo.'}}
               , {'doc': {'name': 'foo', 'description': 'Foo?'}}
               , {'doc': {'name': 'foo', 'description': 'Foo!'}}
                ]
        sync_npm.consume_change_stream(self.change_stream(docs), self.db)

        package = self.db.one('select * from packages')
        assert package.package_manager == 'npm'
        assert package.name == 'foo'
        assert package.description == 'Foo!'
        assert package.emails == []


    def test_consumes_change_stream_with_missing_doc(self):
        docs = [ {'doc': {'name': 'foo', 'description': 'Foo.'}}
               , {'doc': {'name': 'foo', 'description': 'Foo?'}}
               , {'': {'name': 'foo', 'description': 'Foo!'}}
                ]
        sync_npm.consume_change_stream(self.change_stream(docs), self.db)
        package = self.db.one('select * from packages')
        assert package.package_manager == 'npm'
        assert package.name == 'foo'
        assert package.description == 'Foo?'
        assert package.emails == []


    def test_not_afraid_to_delete_docs(self):
        docs = [ {'doc': {'name': 'foo', 'description': 'Foo.'}}
               , {'doc': {'name': 'foo', 'description': 'Foo?'}}
               , {'deleted': True, 'id': 'foo'}
                ]
        sync_npm.consume_change_stream(self.change_stream(docs), self.db)
        assert self.db.one('select * from packages') is None

    def test_delete_tolerates_inexistent_packages(self):
        docs = [{'deleted': True, 'id': 'foo'}]
        sync_npm.consume_change_stream(self.change_stream(docs), self.db)

    def test_even_deletes_package_with_linked_team(self):

        # Set up package linked to team.
        foo = self.make_package()
        alice = self.make_participant('alice')
        with self.db.get_cursor() as cursor:
            team = foo.get_or_create_linked_team(cursor, alice)
        assert self.db.one('select p.*::packages from packages p').team == team

        # Delete package.
        docs = [{'deleted': True, 'id': 'foo'}]
        sync_npm.consume_change_stream(self.change_stream(docs), self.db)
        assert self.db.one('select * from packages') is None

    def test_sets_last_seq(self):
        docs = [{'doc': {'name': 'foo', 'description': 'Foo.'}}] * 13
        assert self.db.one('select npm_last_seq from worker_coordination') == -1
        sync_npm.consume_change_stream(self.change_stream(docs), self.db)
        assert self.db.one('select npm_last_seq from worker_coordination') == 12


    def test_logs_lag(self):
        captured = {}
        def capture(message):
            captured['message'] = message
        self.db.run('update worker_coordination set npm_last_seq=500')
        sync_npm.check(self.db, capture)
        assert captured['message'].startswith('count#npm-sync-lag=')
        assert captured['message'].split('=')[1].isdigit()
