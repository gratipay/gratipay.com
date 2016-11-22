#!/usr/bin/env python
"""verify-identity.py <participant_id> <country_code>
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import sys

from gratipay import wireup
from gratipay.models.participant import Participant
from gratipay.models.country import Country

wireup.db(wireup.env())

participant = Participant.from_id(int(sys.argv[1]))
country = Country.from_code(sys.argv[2])
participant.set_identity_verification(country.id, True)
