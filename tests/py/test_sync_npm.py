# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from subprocess import Popen, PIPE

import pytest

from gratipay.testing import Harness


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
