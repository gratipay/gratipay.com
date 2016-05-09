#!/usr/bin/env python2
"""See gratipay.models.participant.mixins.identity.rekey for documentation.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay import wireup
from gratipay.models.participant.mixins import identity as participant_identities

env = wireup.env()
db = wireup.db(env)
packer = wireup.crypto(env)

n = participant_identities.rekey(db, packer)
print("Rekeyed {} participant identity record(s).".format(n))
