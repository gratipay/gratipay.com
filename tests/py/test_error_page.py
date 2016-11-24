# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing.harness import Harness




class Tests(Harness):

    def test_error_page_doesnt_choke_on_no_user(self):
        try:
            def fail():
                raise Exception
            self.client.website.algorithm.insert_after('parse_environ_into_request', fail)
            response = self.client.GET('/', raise_immediately=False)
            import pdb; pdb.set_trace()
        finally:
            self.client.website.algorithm.remove('fail')
