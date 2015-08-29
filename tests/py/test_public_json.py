from __future__ import print_function, unicode_literals

import json

import pytest
from aspen.utils import utcnow
from gratipay.testing import Harness


class Tests(Harness):

    def make_participant(self, *a, **kw):
        kw['claimed_time'] = utcnow()
        return Harness.make_participant(self, *a, **kw)

    def test_on_key_gives_gratipay(self):
        self.make_participant('alice', last_bill_result='')
        data = json.loads(self.client.GET('/~alice/public.json').body)

        assert data['on'] == 'gratipay'

    @pytest.mark.xfail(reason="#3599")
    def test_anonymous_gets_receiving(self):
        alice = self.make_participant('alice', last_bill_result='')
        bob = self.make_participant('bob')

        alice.set_tip_to(bob, '1.00')

        data = json.loads(self.client.GET('/~bob/public.json').body)

        assert data['receiving'] == '1.00'

    @pytest.mark.xfail(reason="#3599")
    def test_anonymous_does_not_get_my_tip(self):
        alice = self.make_participant('alice', last_bill_result='')
        bob = self.make_participant('bob')

        alice.set_tip_to(bob, '1.00')

        data = json.loads(self.client.GET('/~bob/public.json').body)

        assert data.has_key('my_tip') == False

    @pytest.mark.xfail(reason="#3599")
    def test_anonymous_gets_giving(self):
        alice = self.make_participant('alice', last_bill_result='')
        bob = self.make_participant('bob')

        alice.set_tip_to(bob, '1.00')

        data = json.loads(self.client.GET('/~alice/public.json').body)

        assert data['giving'] == '1.00'

    @pytest.mark.xfail(reason="#3599")
    def test_anonymous_gets_null_giving_if_user_anonymous(self):
        alice = self.make_participant( 'alice'
                                     , last_bill_result=''
                                     , anonymous_giving=True
                                     )
        bob = self.make_participant('bob')
        alice.set_tip_to(bob, '1.00')
        data = json.loads(self.client.GET('/~alice/public.json').body)

        assert data['giving'] == None

    @pytest.mark.xfail(reason="#3599")
    def test_authenticated_user_gets_their_tip(self):
        alice = self.make_participant('alice', last_bill_result='')
        bob = self.make_participant('bob')

        alice.set_tip_to(bob, '1.00')

        raw = self.client.GET('/~bob/public.json', auth_as='alice').body

        data = json.loads(raw)

        assert data['receiving'] == '1.00'
        assert data['my_tip'] == '1.00'

    @pytest.mark.xfail(reason="#3599")
    def test_authenticated_user_doesnt_get_other_peoples_tips(self):
        alice = self.make_participant('alice', last_bill_result='')
        bob = self.make_participant('bob', last_bill_result='')
        carl = self.make_participant('carl', last_bill_result='')
        dana = self.make_participant('dana')

        alice.set_tip_to(dana, '1.00')
        bob.set_tip_to(dana, '3.00')
        carl.set_tip_to(dana, '12.00')

        raw = self.client.GET('/~dana/public.json', auth_as='alice').body

        data = json.loads(raw)

        assert data['receiving'] == '16.00'
        assert data['my_tip'] == '1.00'

    @pytest.mark.xfail(reason="#3599")
    def test_authenticated_user_gets_zero_if_they_dont_tip(self):
        self.make_participant('alice', last_bill_result='')
        bob = self.make_participant('bob', last_bill_result='')
        carl = self.make_participant('carl')

        bob.set_tip_to(carl, '3.00')

        raw = self.client.GET('/~carl/public.json', auth_as='alice').body

        data = json.loads(raw)

        assert data['receiving'] == '3.00'
        assert data['my_tip'] == '0.00'

    @pytest.mark.xfail(reason="#3599")
    def test_authenticated_user_gets_self_for_self(self):
        alice = self.make_participant('alice', last_bill_result='')
        bob = self.make_participant('bob')

        alice.set_tip_to(bob, '3.00')

        raw = self.client.GET('/~bob/public.json', auth_as='bob').body

        data = json.loads(raw)

        assert data['receiving'] == '3.00'
        assert data['my_tip'] == 'self'

    def test_access_control_allow_origin_header_is_asterisk(self):
        self.make_participant('alice', last_bill_result='')
        response = self.client.GET('/~alice/public.json')

        assert response.headers['Access-Control-Allow-Origin'] == '*'

    @pytest.mark.xfail(reason="#3599")
    def test_jsonp_works(self):
        alice = self.make_participant('alice', last_bill_result='')
        bob = self.make_participant('bob')

        alice.set_tip_to(bob, '3.00')

        raw = self.client.GxT('/~bob/public.json?callback=foo', auth_as='bob').body

        assert raw == '''\
foo({
    "avatar": null,
    "cryptocoins": {},
    "elsewhere": {
        "github": {
            "id": %(elsewhere_id)s,
            "user_id": "%(user_id)s",
            "user_name": "bob"
        }
    },
    "giving": "0.00",
    "id": %(user_id)s,
    "my_tip": "self",
    "npatrons": 1,
    "number": "singular",
    "on": "gratipay",
    "receiving": "3.00",
    "username": "bob"
})''' % dict(user_id=bob.id, elsewhere_id=bob.get_accounts_elsewhere()['github'].id)
