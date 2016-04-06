from __future__ import absolute_import, division, print_function, unicode_literals

from aspen import Response
from aspen.http.request import Request
from gratipay import security
from gratipay.testing import Harness
from pytest import raises


class TestSecurity(Harness):

    # oacm - only_allow_certain_methods

    def test_oacm_is_installed_properly(self):
        assert self.client.hxt('TRaCE', '/').code == 405

    def test_oacm_allows_certain_methods(self):
        for allowed in ('GEt', 'HEaD', 'PosT'):
            request = Request(allowed)
            assert security.only_allow_certain_methods(request) is None

    def test_oacm_disallows_a_bunch_of_other_stuff(self):
        for disallowed in ('OPTIONS', 'TRACE', 'TRACK', 'PUT', 'DELETE'):
            request = Request(disallowed)
            response = raises(Response, security.only_allow_certain_methods, request).value
            assert response.code == 405

    def test_oacm_doesnt_choke_error_handling(self):
        assert self.client.hit("OPTIONS", "/", raise_immediately=False).code == 405


    # ahtr - add_headers_to_response

    def test_ahtr_sets_x_frame_options(self):
        headers = self.client.GET('/about/').headers
        assert headers['X-Frame-Options'] == 'SAMEORIGIN'

    def test_ahtr_sets_x_content_type_options(self):
        headers = self.client.GET('/about/').headers
        assert headers['X-Content-Type-Options'] == 'nosniff'

    def test_ahtr_sets_x_xss_protection(self):
        headers = self.client.GET('/about/').headers
        assert headers['X-XSS-Protection'] == '1; mode=block'
