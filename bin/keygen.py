#!/usr/bin/env python2
from __future__ import absolute_import, division, print_function, unicode_literals
from cryptography.fernet import Fernet
print(Fernet.generate_key())
