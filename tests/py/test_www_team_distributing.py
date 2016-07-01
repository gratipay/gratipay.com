from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing import Harness


class Tests(Harness):

    def test_distributing_redirects_when_no_money_is_available(self):
        self.make_team()
        assert self.client.GxT('/TheEnterprise/distributing/').code == 302

    def test_distributing_doesnt_redirect_when_money_is_available(self):
        self.make_team()
        self.db.run("UPDATE teams SET available=537")
        assert self.client.GET('/TheEnterprise/distributing/').code == 200


    def test_json_redirects_when_no_money_is_available(self):
        self.make_team()
        assert self.client.GxT('/TheEnterprise/distributing/index.json').code == 302

    def test_json_doesnt_redirect_when_money_is_available(self):
        self.make_team()
        self.db.run("UPDATE teams SET available=537")
        assert self.client.GET('/TheEnterprise/distributing/index.json', raise_immediately=False).code == 500


    def test_member_json_redirects_when_no_money_is_available(self):
        self.make_team()
        assert self.client.GxT('/TheEnterprise/distributing/1.json').code == 302

    def test_member_json_doesnt_redirect_when_money_is_available(self):
        self.make_team()
        self.db.run("UPDATE teams SET available=537")
        assert self.client.GET('/TheEnterprise/distributing/1.json', raise_immediately=False).code == 500
