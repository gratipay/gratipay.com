# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from subprocess import Popen, PIPE

import pytest

from gratipay.testing import Harness, skipif_missing_marky_markdown
from gratipay.sync_npm import fetch_readmes, process_readmes


def load(raw):
    serialized = Popen( ('env/bin/sync-npm', 'serialize', '/dev/stdin')
                      , stdin=PIPE, stdout=PIPE
                       ).communicate(raw)[0]
    Popen( ('env/bin/sync-npm', 'upsert', '/dev/stdin')
         , stdin=PIPE, stdout=PIPE
          ).communicate(serialized)[0]


class Sentrifier:

    def __init__(self):
        self.ncalls = 0

    def __call__(self, func):
        def _(*a, **kw):
            try:
                func(*a, **kw)
            except:
                self.ncalls += 1
        return _

    def fail(self, *a, **kw):
        raise RuntimeError


class Tests(Harness):

    def test_packages_starts_empty(self):
        assert self.db.all('select * from packages') == []


    # sn - sync-npm

    def test_sn_inserts_packages(self):
        load(br'''
        { "_updated": 1234567890
        , "testing-package":
            { "name":"testing-package"
            , "description":"A package for testing"
            , "maintainers":[{"email":"alice@example.com"}]
            , "author": {"email":"bob@example.com"}
            , "time":{"modified":"2015-09-12T03:03:03.135Z"}
             }
         }
        ''')

        package = self.db.one('select * from packages')
        assert package.package_manager == 'npm'
        assert package.name == 'testing-package'
        assert package.description == 'A package for testing'
        assert package.name == 'testing-package'


    def test_sn_handles_quoting(self):
        load(br'''
        { "_updated": 1234567890
        , "testi\\\"ng-pa\\\"ckage":
            { "name":"testi\\\"ng-pa\\\"ckage"
            , "description":"A package for \"testing\""
            , "maintainers":[{"email":"alice@\"example\".com"}]
            , "author": {"email":"\\\\\"bob\\\\\"@example.com"}
            , "time":{"modified":"2015-09-12T03:03:03.135Z"}
             }
         }
        ''')

        package = self.db.one('select * from packages')
        assert package.package_manager == 'npm'
        assert package.name == r'testi\"ng-pa\"ckage'
        assert package.description == 'A package for "testing"'
        assert package.emails == ['alice@"example".com', r'\\"bob\\"@example.com']


    def test_sn_handles_empty_description_and_emails(self):
        load(br'''
        { "_updated": 1234567890
        , "empty-description":
            { "name":"empty-description"
            , "description":""
            , "time":{"modified":"2015-09-12T03:03:03.135Z"}
             }
         }
        ''')

        package = self.db.one('select * from packages')
        assert package.package_manager == 'npm'
        assert package.name == 'empty-description'
        assert package.description == ''
        assert package.emails == []


    # sentrifier

    def test_sentrifier_starts_at_zero(self):
        sentrified = Sentrifier()
        assert sentrified.ncalls == 0

    def test_sentrifier_fail_fails(self):
        pytest.raises(RuntimeError, Sentrifier().fail)


    # fr - fetch_readmes

    def make_package_without_readme_raw(self):
        self.db.run("INSERT INTO packages (package_manager, name, description, emails) "
                    "VALUES ('npm', 'foo-package', 'A package', ARRAY[]::text[])")

    def test_fr_fetches_a_readme(self):
        self.make_package_without_readme_raw()

        def fetch(name):
            return 200, {'name': 'foo-package', 'readme': '# Greetings, program!'}

        fetch_readmes.main({}, [], self.db, lambda a: a, fetch)

        package = self.db.one('SELECT * FROM packages')
        assert package.name == 'foo-package'
        assert package.description == 'A package'
        assert package.readme == ''
        assert package.readme_needs_to_be_processed
        assert package.readme_raw == '# Greetings, program!'
        assert package.readme_type == 'x-markdown/marky'
        assert package.emails == []

    def test_fr_adds_empty_readme_as_needed(self):
        self.make_package_without_readme_raw()
        def fetch(name):
            return 200, {'name': 'foo-package', 'redmeat': '# Greetings, program!'}
        fetch_readmes.main({}, [], self.db, lambda a: a, fetch)
        package = self.db.one('SELECT * FROM packages')
        assert package.readme_raw == ''

    def test_fr_replaces_non_unicode_with_empty_readme(self):
        self.make_package_without_readme_raw()
        def fetch(name):
            return 200, {'name': 'foo-package', 'readme': {'private': True}}
        fetch_readmes.main({}, [], self.db, lambda a: a, fetch)
        package = self.db.one('SELECT * FROM packages')
        assert package.readme_raw == ''

    def test_fr_deletes_a_readme(self):
        self.make_package_without_readme_raw()
        fetch_readmes.main({}, [], self.db, lambda a: a, lambda n: (404, {}))
        assert self.db.one('SELECT * FROM packages') is None

    def test_fr_tells_sentry_about_problems(self):
        self.make_package_without_readme_raw()
        sentrified = Sentrifier()
        fetch_readmes.main({}, [], self.db, sentrified, sentrified.fail)
        assert sentrified.ncalls == 1


    # pr - process_readmes

    def make_package_with_readme_raw(self):
        self.db.run('''

            INSERT
              INTO packages (package_manager, name, description, readme_raw, readme_type, emails)
            VALUES ('npm', 'foo-package', 'A package', '# Foo Package\nA package',
                    'x-markdown/marky', ARRAY[]::text[])

        ''')

    @skipif_missing_marky_markdown
    def test_pr_processes_a_readme(self):
        self.make_package_with_readme_raw()

        process_readmes.main({}, [], self.db, lambda a: a)

        package = self.db.one('SELECT * FROM packages')
        assert package.name == 'foo-package'
        assert package.description == 'A package'
        assert package.readme == '<h1 class="package-name-redundant package-description-redundant"><a id="user-content-foo-package" class="deep-link" href="#foo-package"><svg aria-hidden="true" class="deep-link-icon" height="16" version="1.1" width="16"><path d="M4 9h1v1H4c-1.5 0-3-1.69-3-3.5S2.55 3 4 3h4c1.45 0 3 1.69 3 3.5 0 1.41-.91 2.72-2 3.25V8.59c.58-.45 1-1.27 1-2.09C10 5.22 8.98 4 8 4H4c-.98 0-2 1.22-2 2.5S3 9 4 9zm9-3h-1v1h1c1 0 2 1.22 2 2.5S13.98 12 13 12H9c-.98 0-2-1.22-2-2.5 0-.83.42-1.64 1-2.09V6.25c-1.09.53-2 1.84-2 3.25C6 11.31 7.55 13 9 13h4c1.45 0 3-1.69 3-3.5S14.5 6 13 6z"></path></svg></a>Foo Package</h1>\n<p class="package-description-redundant">A package</p>\n'
        assert not package.readme_needs_to_be_processed
        assert package.readme_raw == '# Foo Package\nA package'
        assert package.readme_type == 'x-markdown/marky'
        assert package.emails == []


    def test_pr_tells_sentry_about_problems(self):
        self.make_package_with_readme_raw()
        sentrified = Sentrifier()
        process_readmes.main({}, [], self.db, sentrified, sentrified.fail)
        assert sentrified.ncalls == 1
