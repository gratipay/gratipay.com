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

    def change_stream(self, docs):
        def change_stream(seq):
            for i, doc in enumerate(docs):
                if i < seq: continue
                yield {'seq': i, 'doc': doc}
        return change_stream


    def test_packages_starts_empty(self):
        assert self.db.all('select * from packages') == []


    def test_consumes_change_stream(self):
        docs = [ {'name': 'foo', 'description': 'Foo.'}
               , {'name': 'foo', 'description': 'Foo?'}
               , {'name': 'foo', 'description': 'Foo!'}
                ]
        sync_npm.consume_change_stream(self.change_stream(docs), self.db)

        package = self.db.one('select * from packages')
        assert package.package_manager == 'npm'
        assert package.name == 'foo'
        assert package.description == 'Foo!'
        assert package.emails == []


    def test_picks_up_with_last_seq(self):
        docs = [ {'name': 'foo', 'description': 'Foo.'}
               , {'name': 'foo', 'description': 'See alice?', 'maintainers': [{'email': 'alice'}]}
               , {'name': 'foo', 'description': "No, I don't see alice!"}
                ]
        self.db.run('update worker_coordination set npm_last_seq=2')
        sync_npm.consume_change_stream(self.change_stream(docs), self.db)

        package = self.db.one('select * from packages')
        assert package.description == "No, I don't see alice!"
        assert package.emails == []


    def test_sets_last_seq(self):
        docs = [{'name': 'foo', 'description': 'Foo.'}] * 13
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
