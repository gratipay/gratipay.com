from gratipay.testing import Harness


class Tests(Harness):

    def setUp(self):
        self.alice = self.make_participant('alice', claimed_time='now', is_admin=True)
        self.bob = self.make_participant('bob', claimed_time='now')


    # il - identities listing

    def test_il_is_403_for_anon(self):
        assert self.client.GxT('/~bob/identities/').code == 403

    def test_il_is_403_for_non_admin(self):
        assert self.client.GxT('/~bob/identities/').code == 403

    def test_il_is_200_for_self(self):
        assert self.client.GET('/~bob/identities/', auth_as='alice').code == 200

    def test_il_is_200_for_admin(self):
        assert self.client.GET('/~bob/identities/', auth_as='alice').code == 200


    # ip - identity page

    def test_ip_is_403_for_anon(self):
        assert self.client.GxT('/~bob/identities/TT').code == 403

    def test_ip_is_403_for_non_admin(self):
        assert self.client.GxT('/~bob/identities/TT').code == 403

    def test_ip_is_200_for_self(self):
        assert self.client.GET('/~bob/identities/TT', auth_as='alice').code == 200

    def test_ip_is_200_for_admin(self):
        assert self.client.GET('/~bob/identities/TT', auth_as='alice').code == 200

    def test_ip_(self):
        pass
