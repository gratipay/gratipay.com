from __future__ import absolute_import, division, print_function, unicode_literals

import hashlib
import json
import random
import string
import time
import hmac

from cryptography.fernet import Fernet, MultiFernet


# utils
# =====
# borrowed from Django

try:                                # use the system PRNG if possible
    random = random.SystemRandom()
    using_sysrandom = True
except NotImplementedError:         # fall back
    import warnings
    warnings.warn('A secure pseudo-random number generator is not available '
                  'on your system. Falling back to Mersenne Twister.')
    using_sysrandom = False

pool = string.digits + string.letters + string.punctuation
UNSECURE_RANDOM_STRING = b"".join([random.choice(pool) for i in range(64)])


def get_random_string(length=12,
                      allowed_chars='abcdefghijklmnopqrstuvwxyz'
                                    'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'):
    """
    Returns a securely generated random string.

    The default length of 12 with the a-z, A-Z, 0-9 character set returns
    a 71-bit value. log_2((26+26+10)^12) =~ 71 bits
    """
    if not using_sysrandom:
        # This is ugly, and a hack, but it makes things better than
        # the alternative of predictability. This re-seeds the PRNG
        # using a value that is hard for an attacker to predict, every
        # time a random string is required. This may change the
        # properties of the chosen random sequence slightly, but this
        # is better than absolute predictability.
        random.seed(
            hashlib.sha256(
                "%s%s%s" % (
                    random.getstate(),
                    time.time(),
                    UNSECURE_RANDOM_STRING)
                ).digest())
    return ''.join([random.choice(allowed_chars) for i in range(length)])


def constant_time_compare(val1, val2):
    """
    Returns True if the two strings are equal, False otherwise.

    The time taken is independent of the number of characters that match.
    https://codahale.com/a-lesson-in-timing-attacks/
    """
    return hmac.compare_digest(bytes(val1), bytes(val2))


# Encrypting Packer
# =================

class EncryptingPacker(object):
    """Implement conversion of Python objects to/from encrypted bytestrings.

    :param str key: a `Fernet`_ key to use for encryption and decryption
    :param list old_keys: additional `Fernet`_ keys to use for decryption

    .. note::

        Encrypted messages contain the timestamp at which they were generated
        *in plaintext*. See `our audit`_ for discussion of this and other
        considerations with `Fernet`_.

    .. _Fernet: https://cryptography.io/en/latest/fernet/
    .. _our audit: https://github.com/gratipay/gratipay.com/pull/3998#issuecomment-216227070

    """

    def __init__(self, key, *old_keys):
        keys = [key] + list(old_keys)
        self.fernet = MultiFernet([Fernet(k) for k in keys])

    def pack(self, obj):
        """Given a JSON-serializable object, return a `Fernet`_ token.
        """
        obj = json.dumps(obj)           # serialize to unicode
        obj = obj.encode('utf8')        # convert to bytes
        obj = self.fernet.encrypt(obj)  # encrypt
        return obj

    def unpack(self, token):
        """Given a `Fernet`_ token with JSON in the ciphertext, return a Python object.
        """
        obj = token
        if not type(obj) is bytes:
            raise TypeError("need bytes, got {}".format(type(obj)))
        obj = self.fernet.decrypt(obj)  # decrypt
        obj = obj.decode('utf8')        # convert to unicode
        obj = json.loads(obj)           # deserialize from unicode
        return obj
