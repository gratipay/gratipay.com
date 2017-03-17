from __future__ import unicode_literals

import json

from gratipay.testing import Harness
from gratipay.testing.billing import PaydayMixin


class Tests(Harness, PaydayMixin):

    def test_paydays_json_gives_paydays(self):
        self.start_payday()
        self.make_participant("alice")

        response = self.client.GET("/about/paydays.json")
        paydays = json.loads(response.body)
        assert paydays[0]['nusers'] == 0
