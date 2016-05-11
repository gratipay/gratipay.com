from __future__ import absolute_import, division, print_function, unicode_literals

import struct
import datetime

from aspen import Response
from aspen.http.request import Request
from base64 import urlsafe_b64decode
from cryptography.fernet import Fernet, InvalidToken
from gratipay import security
from gratipay.models.participant.mixins import Identity
from gratipay.security.crypto import EncryptingPacker
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


    # ep - EncryptingPacker

    packed = b'gAAAAABXJMbdriJ984uMCMKfQ5p2UUNHB1vG43K_uJyzUffbu2Uwy0d71kAnqOKJ7Ww_FEQz9Dliw87UpM'\
             b'5TdyoJsll5nMAicg=='

    def test_ep_packs_encryptingly(self):
        packed = Identity.encrypting_packer.pack({"foo": "bar"})
        assert urlsafe_b64decode(packed)[0] == b'\x80'  # Fernet version

    def test_ep_unpacks_decryptingly(self):
        assert Identity.encrypting_packer.unpack(self.packed) == {"foo": "bar"}

    def test_ep_fails_to_unpack_old_data_with_a_new_key(self):
        encrypting_packer = EncryptingPacker(Fernet.generate_key())
        raises(InvalidToken, encrypting_packer.unpack, self.packed)

    def test_ep_can_unpack_if_old_key_is_provided(self):
        old_key = str(self.client.website.env.crypto_keys)
        encrypting_packer = EncryptingPacker(Fernet.generate_key(), old_key)
        assert encrypting_packer.unpack(self.packed) == {"foo": "bar"}

    def test_ep_leaks_timestamp_derp(self):
        # https://github.com/pyca/cryptography/issues/2714
        timestamp, = struct.unpack(">Q", urlsafe_b64decode(self.packed)[1:9])  # unencrypted!
        assert datetime.datetime.fromtimestamp(timestamp).year == 2016

    def test_ep_demands_bytes(self):
        raises(TypeError, Identity.encrypting_packer.unpack, buffer('buffer'))
        raises(TypeError, Identity.encrypting_packer.unpack, 'unicode')
