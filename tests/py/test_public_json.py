from __future__ import print_function, unicode_literals

import json

from aspen.utils import utcnow
from gratipay.testing import Harness
from gratipay.models.participant import Participant


class Tests(Harness):

    def make_participant(self, *a, **kw):
        kw['claimed_time'] = utcnow()
        return Harness.make_participant(self, *a, **kw)

    def test_on_key_gives_gratipay(self):
        self.make_participant('alice', last_bill_result='')
        data = json.loads(self.client.GET('/~alice/public.json').body)
        assert data['on'] == 'gratipay'

    def test_anonymous_gets_taking(self):
        alice = self.make_participant('alice', last_bill_result='')
        Enterprise = self.make_team(is_approved=True)
        alice.set_payment_instruction(Enterprise, '1.00')
        data = json.loads(self.client.GET('/~picard/public.json').body)
        assert data['taking'] == '1.00'

    def test_anonymous_gets_giving(self):
        alice = self.make_participant('alice', last_bill_result='')
        Enterprise = self.make_team(is_approved=True)
        alice.set_payment_instruction(Enterprise, '1.00')
        data = json.loads(self.client.GET('/~alice/public.json').body)
        assert data['giving'] == '1.00'

    def test_anonymous_gets_null_giving_if_user_anonymous(self):
        alice = self.make_participant('alice', last_bill_result='', anonymous_giving=True)
        Enterprise = self.make_team(is_approved=True)
        alice.set_payment_instruction(Enterprise, '1.00')
        data = json.loads(self.client.GET('/~alice/public.json').body)
        assert data['giving'] == None

    def test_access_control_allow_origin_header_is_asterisk(self):
        self.make_participant('alice', last_bill_result='')
        response = self.client.GET('/~alice/public.json')
        assert response.headers['Access-Control-Allow-Origin'] == '*'

    def test_jsonp_works(self):
        alice = self.make_participant('alice', last_bill_result='')
        Enterprise = self.make_team(is_approved=True)
        alice.set_payment_instruction(Enterprise, '3.00')
        picard = Participant.from_username('picard')
        raw = self.client.GxT('/~picard/public.json?callback=foo', auth_as='picard').body
        assert raw == '''\
foo({
    "avatar": null,
    "cryptocoins": {},
    "elsewhere": {
        "github": {
            "id": %(elsewhere_id)s,
            "user_id": "%(user_id)s",
            "user_name": "picard"
        }
    },
    "giving": "0.00",
    "id": %(user_id)s,
    "number": "singular",
    "on": "gratipay",
    "taking": "3.00",
    "username": "picard"
})''' % dict(user_id=picard.id, elsewhere_id=picard.get_accounts_elsewhere()['github'].id)
