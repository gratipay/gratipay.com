from __future__ import absolute_import, division, print_function, unicode_literals

import struct
import datetime

from aspen import Response
from aspen.http.request import Request
from base64 import urlsafe_b64decode
from cryptography.fernet import Fernet, InvalidToken
from gratipay import security
from gratipay.models.participant import Identity
from gratipay.security.crypto import EncryptingPacker
from gratipay.testing import Harness
from pytest import raises


class RejectNullBytesInURI(Harness):

    def test_filters_path(self):
        assert self.client.GxT('/f%00/').code == 400

    def test_filters_querystring(self):
        assert self.client.GxT('/', QUERY_STRING='f%00=bar').code == 400

    def test_protects_against_reflected_xss(self):
        self.make_package()
        assert self.client.GET('/on/npm/foo').code == 200
        assert self.client.GxT('/on/npm/foo%00<svg onload=alert(1)>').code == 400
        assert self.client.GxT('/on/npm/foo%01<svg onload=alert(1)>').code == 404 # fyi


class OnlyAllowCertainMethodsTests(Harness):

    def test_is_installed_properly(self):
        assert self.client.hxt('TRaCE', '/').code == 405

    def test_allows_certain_methods(self):
        for allowed in ('GEt', 'HEaD', 'PosT'):
            request = Request(allowed)
            assert security.only_allow_certain_methods(request) is None

    def test_disallows_a_bunch_of_other_stuff(self):
        for disallowed in ('OPTIONS', 'TRACE', 'TRACK', 'PUT', 'DELETE'):
            request = Request(disallowed)
            response = raises(Response, security.only_allow_certain_methods, request).value
            assert response.code == 405

    def test_doesnt_choke_error_handling(self):
        assert self.client.hit("OPTIONS", "/", raise_immediately=False).code == 405

    def test_prevents_csrf_from_choking(self):
        assert self.client.PxST('/assets/gratipay.css').code == 405


class AddHeadersToResponseTests(Harness):

    def test_sets_x_frame_options(self):
        headers = self.client.GET('/about/').headers
        assert headers['X-Frame-Options'] == 'SAMEORIGIN'

    def test_sets_x_content_type_options(self):
        headers = self.client.GET('/about/').headers
        assert headers['X-Content-Type-Options'] == 'nosniff'

    def test_sets_x_xss_protection(self):
        headers = self.client.GET('/about/').headers
        assert headers['X-XSS-Protection'] == '1; mode=block'

    def test_sets_referrer_policy(self):
        headers = self.client.GET('/about/').headers
        assert headers['Referrer-Policy'] == \
                                      'no-referrer-when-downgrade, strict-origin-when-cross-origin'

    def test_sets_strict_transport_security(self):
        headers = self.client.GET('/about/').headers
        assert headers['strict-transport-security'] == 'max-age=31536000'

    def test_doesnt_set_content_security_policy_by_default(self):
        assert 'content-security-policy-report-only' not in self.client.GET('/about/').headers

    def test_sets_content_security_policy(self):
        with self.setenv(CSP_REPORT_URI='http://cheese/'):
            headers = self.client.GET('/about/').headers
            policy = (
                "default-src 'self';"
                "script-src 'self' assets.gratipay.com 'unsafe-inline';"
                "style-src 'self' assets.gratipay.com downloads.gratipay.com cloud.typography.com"
                "          'sha256-WLocK7HeCKzQLS0M+PGS++5IhyfFsOA5N4ZCeTcltoo=';"
                "img-src *;"
                "font-src 'self' assets.gratipay.com cloud.typography.com data:;"
                "block-all-mixed-content;"
                "report-uri http://cheese/;"
            )
            assert headers['content-security-policy-report-only'] == policy


class EncryptingPackerTests(Harness):

    packed = b'gAAAAABXJMbdriJ984uMCMKfQ5p2UUNHB1vG43K_uJyzUffbu2Uwy0d71kAnqOKJ7Ww_FEQz9Dliw87UpM'\
             b'5TdyoJsll5nMAicg=='

    def test_packs_encryptingly(self):
        packed = Identity.encrypting_packer.pack({"foo": "bar"})
        assert urlsafe_b64decode(packed)[0] == b'\x80'  # Fernet version

    def test_unpacks_decryptingly(self):
        assert Identity.encrypting_packer.unpack(self.packed) == {"foo": "bar"}

    def test_fails_to_unpack_old_data_with_a_new_key(self):
        encrypting_packer = EncryptingPacker(Fernet.generate_key())
        raises(InvalidToken, encrypting_packer.unpack, self.packed)

    def test_can_unpack_if_old_key_is_provided(self):
        old_key = str(self.client.website.env.crypto_keys)
        encrypting_packer = EncryptingPacker(Fernet.generate_key(), old_key)
        assert encrypting_packer.unpack(self.packed) == {"foo": "bar"}

    def test_leaks_timestamp_derp(self):
        # https://github.com/pyca/cryptography/issues/2714
        timestamp, = struct.unpack(">Q", urlsafe_b64decode(self.packed)[1:9])  # unencrypted!
        assert datetime.datetime.fromtimestamp(timestamp).year == 2016

    def test_demands_bytes(self):
        raises(TypeError, Identity.encrypting_packer.unpack, buffer('buffer'))
        raises(TypeError, Identity.encrypting_packer.unpack, 'unicode')
