"""Tests for syncing npm. Requires a `pip install ijson`, which requires yajl. Good luck! :^)
"""
from __future__ import absolute_import, division, print_function, unicode_literals

from subprocess import Popen, PIPE

import pytest
from gratipay.utils import markdown
from gratipay.testing import Harness
from gratipay.package_managers import readmes, sync


def load(raw):
    serialized = Popen( ('env/bin/sync-npm', 'serialize', '/dev/stdin')
                      , stdin=PIPE, stdout=PIPE
                       ).communicate(raw)[0]
    Popen( ('env/bin/sync-npm', 'upsert', '/dev/stdin')
         , stdin=PIPE, stdout=PIPE
          ).communicate(serialized)[0]


try:
    sync.import_ijson()
except ImportError:
    missing_ijson = True
else:
    missing_ijson = False

try:
    markdown.marky('test')
except OSError:
    missing_marky_markdown = True
else:
    missing_marky_markdown = False

@pytest.mark.skipif(missing_ijson, reason="missing ijson")
@pytest.mark.skipif(missing_marky_markdown, reason="missing marky-markdown")
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


    # rs - readmes.Syncer

    def test_rs_syncs_a_readme(self):
        self.db.run("INSERT INTO packages (package_manager, name, description, emails) "
                    "VALUES ('npm', 'foo-package', 'A package', ARRAY[]::text[])")

        class DirtyPackage:
            package_manager = 'npm'
            name = 'foo-package'

        def fetch(name):
            return {'name': 'foo-package', 'readme': '# Greetings, program!'}

        readmes.Syncer(self.db)(DirtyPackage(), fetch=fetch)

        package = self.db.one('SELECT * FROM packages')
        assert package.name == 'foo-package'
        assert package.description == 'A package'
        assert package.readme == '<h1><a id="user-content-greetings-program" class="deep-link" href="#greetings-program"><svg aria-hidden="true" class="deep-link-icon" height="16" version="1.1" width="16"><path d="M4 9h1v1H4c-1.5 0-3-1.69-3-3.5S2.55 3 4 3h4c1.45 0 3 1.69 3 3.5 0 1.41-.91 2.72-2 3.25V8.59c.58-.45 1-1.27 1-2.09C10 5.22 8.98 4 8 4H4c-.98 0-2 1.22-2 2.5S3 9 4 9zm9-3h-1v1h1c1 0 2 1.22 2 2.5S13.98 12 13 12H9c-.98 0-2-1.22-2-2.5 0-.83.42-1.64 1-2.09V6.25c-1.09.53-2 1.84-2 3.25C6 11.31 7.55 13 9 13h4c1.45 0 3-1.69 3-3.5S14.5 6 13 6z"></path></svg></a>Greetings, program!</h1>\n'
        assert package.readme_raw == '# Greetings, program!'
        assert package.readme_type == 'x-markdown/npm'
        assert package.emails == []
