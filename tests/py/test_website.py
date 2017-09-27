# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing import Harness


class UpdateCTA(Harness):

    def test_sets_campaign_things_when_empty(self):
        assert self.client.website.campaign_npayments == 0
        assert self.client.website.campaign_raised == 0
