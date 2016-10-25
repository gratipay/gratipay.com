from __future__ import absolute_import, division, print_function, unicode_literals

from subprocess import Popen, PIPE

from gratipay.testing import Harness


CATALOG = b'''\
{ "_updated": 1234567890
, "testing-package":
    { "name":"testing-package"
    , "description":"A package for testing"
    , "maintainers":[{"email":"alice@example.com"}]
    , "author": {"email":"bob@example.com"}
    , "time":{"modified":"2015-09-12T03:03:03.135Z"}
     }
 }
'''


class Tests(Harness):

    def test_packages_starts_empty(self):
        assert self.db.all('select * from packages') == []


    def test_npm_inserts_packages(self):
        serialize = Popen( ('env/bin/python', 'bin/npm.py', 'serialize', '/dev/stdin')
                         , stdin=PIPE
                         , stdout=PIPE
                          )
        upsert = Popen( ('env/bin/python', 'bin/npm.py', 'upsert', '/dev/stdin')
                      , stdin=serialize.stdout
                      , stdout=PIPE
                       )
        serialize.communicate(CATALOG)
        serialize.wait()
        upsert.wait()
        assert self.db.one('select * from packages').name == 'testing-package'
