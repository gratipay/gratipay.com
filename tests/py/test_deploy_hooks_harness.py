# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from filesystem_tree import FilesystemTree
from gratipay.testing import DeployHooksHarness
from psycopg2 import ProgrammingError
from pytest import raises


AFTER_PY = '''\
from gratipay import wireup

db = wireup.db(wireup.env())
db.run('INSERT INTO foo (bar) VALUES (42), (537)')
'''


class RunDeployHooks(DeployHooksHarness):

    def setUp(self):
        self.ft = FilesystemTree()
        self.db.run('DROP TABLE IF EXISTS foo;')

    def tearDown(self):
        self.ft.remove()
        self.db.run('DROP TABLE IF EXISTS foo;')

    def test_runs_deploy_hooks(self):
        self.ft.mk( ('before.sql', 'CREATE TABLE foo (bar int);')
                  , ('after.py', AFTER_PY)
                  , ('after.sql', 'ALTER TABLE foo RENAME COLUMN bar TO baz;')
                   )

        raises(ProgrammingError, self.db.all, 'SELECT name FROM foo')
        self.run_deploy_hooks(_deploy_dir=self.ft.root)
        assert self.db.all('SELECT baz FROM foo ORDER BY baz') == [42, 537]
