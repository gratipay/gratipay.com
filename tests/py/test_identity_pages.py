from gratipay.testing import Harness
from gratipay.models.country import Country
from gratipay.models.participant import Participant


class Tests(Harness):

    def setUp(self):
        self.make_participant('alice', claimed_time='now', is_admin=True)
        self.make_participant('whit537', id=1451, email_address='chad@zetaweb.com',
            claimed_time='now', is_admin=True)
        self.make_participant('bob', claimed_time='now', email_address='bob@example.com')
        self.verify('bob', 'TT')

    def identify(self, username, *codes):
        participant = Participant.from_username(username)
        for code in codes:
            country_id = Country.from_code(code).id
            participant.store_identity_info(country_id, 'nothing-enforced', {})
        return participant

    def verify(self, username, *codes):
        participant = Participant.from_username(username)
        for code in codes:
            country_id = Country.from_code(code).id
            participant.store_identity_info(country_id, 'nothing-enforced', {})
            participant.set_identity_verification(country_id, True)
        return participant


    # il - identities listing

    def test_il_is_403_for_anon(self):
        assert self.client.GxT('/~bob/identities/').code == 403

    def test_il_is_403_for_non_admin(self):
        assert self.client.GxT('/~bob/identities/').code == 403

    def test_il_is_200_for_self(self):
        assert self.client.GET('/~bob/identities/', auth_as='bob').code == 200

    def test_il_is_200_for_admin(self):
        assert self.client.GET('/~bob/identities/', auth_as='alice').code == 200


    # ip - identity page

    def test_ip_is_403_for_anon(self):
        assert self.client.GxT('/~bob/identities/TT').code == 403

    def test_ip_is_403_for_non_admin(self):
        assert self.client.GxT('/~bob/identities/TT').code == 403

    def test_ip_is_200_for_self(self):
        assert self.client.GET('/~bob/identities/TT', auth_as='bob').code == 200

    def test_ip_is_403_for_most_admins(self):
        assert self.client.GxT('/~bob/identities/TT', auth_as='alice').code == 403

    def test_ip_is_200_for_whit537_yikes(self):
        assert self.client.GET('/~bob/identities/TT', auth_as='whit537').code == 200

    def test_ip_is_404_for_unknown_code(self):
        assert self.client.GxT('/~bob/identities/XX', auth_as='bob').code == 404

    def test_ip_is_302_if_no_verified_email(self):
        response = self.client.GxT('/~alice/identities/TT', auth_as='alice')
        assert response.code == 302
        assert response.headers['Location'] == '/about/me/emails/'


    def test_ip_is_200_for_third_identity(self):
        self.verify('bob', 'TT', 'US')
        assert self.client.GET('/~bob/identities/US', auth_as='bob').code == 200

    def test_ip_is_302_for_fourth_identity(self):
        self.verify('bob', 'TT', 'US', 'GB')
        assert self.client.GxT('/~bob/identities/CA', auth_as='bob').code == 302

    def test_ip_is_302_for_fifth_identities(self):
        self.verify('bob', 'TT', 'US', 'GB', 'GH')
        assert self.client.GxT('/~bob/identities/CA', auth_as='bob').code == 302

    def test_but_ip_always_loads_for_own_identity(self):
        self.verify('bob', 'TT', 'US', 'GB', 'GH')
        assert self.client.GET('/~bob/identities/TT', auth_as='bob').code == 200

    def test_ip_always_loads_for_own_identity_even_if_unverified(self):
        self.verify('bob', 'US', 'GB', 'GH')
        self.identify('bob', 'TT')
        assert self.client.GET('/~bob/identities/TT', auth_as='bob').code == 200


    def test_ip_removes_identity(self):
        bob = self.verify('bob', 'TT')
        assert len(bob.list_identity_metadata()) == 1
        data = {'action': 'remove'}
        assert self.client.PxST('/~bob/identities/TT', auth_as='bob', data=data).code == 302
        assert len(bob.list_identity_metadata()) == 0

    def test_ip_stores_identity(self):
        bob = Participant.from_username('bob')
        assert len(bob.list_identity_metadata()) == 1
        data = { 'id_type':     ''
               , 'id_number':   ''
               , 'legal_name':  'Bobsworth B. Bobbleton, IV'
               , 'dob':         ''
               , 'address_1':   ''
               , 'address_2':   ''
               , 'city':        ''
               , 'region':      ''
               , 'postcode':    ''
               , 'action':      'store'
                }
        assert self.client.PxST('/~bob/identities/US', auth_as='bob', data=data).code == 302
        assert len(bob.list_identity_metadata()) == 2
        info = bob.retrieve_identity_info(Country.from_code('US').id)
        assert info['legal_name'] == 'Bobsworth B. Bobbleton, IV'

    def test_ip_validates_action(self):
        bob = Participant.from_username('bob')
        assert len(bob.list_identity_metadata()) == 1
        data = {'action': 'cheese'}
        assert self.client.PxST('/~bob/identities/TT', auth_as='bob', data=data).code == 400
        assert len(bob.list_identity_metadata()) == 1
