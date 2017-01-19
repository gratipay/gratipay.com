from __future__ import absolute_import, division, print_function, unicode_literals

import json
import mock
import pytest
import base64

from aspen.testing.client import FileUpload
from gratipay.testing import Harness, D,T
from gratipay.models.team import Team, slugize, InvalidTeamName


REVIEW_URL = "https://github.com/gratipay/test-gremlin/issues/9"

IMAGE = base64.b64decode(b"""\
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
07bedrX2phuSN2o6eDvKOhk787vIu9K7NruTuld6InuWbgbcnO316H16y/nWw9s2t4f7zPru9hv2
37qjc6f7rsbdjgHVgbZ7yvdaBhUHm4cUhpr+UviraVhxuPm+0v3WEZWR9lH10a4xrbGbD/Qf9D80
eTg4bjk+OuEw8fjR7kdTj30fv3kS+uTjZNzk2tOUZ9hnOc9pnhe/4HhR9VL0Zf2U4lTntP700Izd
zNNZn9m3r6Jfrc+lv6Z6XTzPPV/7RvZNx4Lhwsii2+Lc28i3a0uZ72jflb8XeX/9g/aHoWXn5bmP
pI+bnw5/Zv1c80X+S++K9cqLr2Ff177lrLKuXviu/P3OD6cf82vx6/j1kg3RjfafZj+fbYZtbkZ6
kby2rwIIWmF/fwA+1QBA5QIAPZrHkRN38q9fBYG20g4A8OhNwRS9AcxCYui53QOzwjHwJGKC3MIY
YR5iw3C0uF78XoImGZ7sOXkbRTllPlUN8RkNDa0ZXTb9ACMt027mS6wYNi/2Tk4ersPcq7y+fJMC
loIDwlIieaJvxU12VUp8ldKTPiIzIkclr6sQrViu1KM8pbKhxqwurqGiaaBlq+2jE62brndCv86g
2/CB0YLxpimj2S5zPQs3yyCrOOsMm0LbSrs6+xZ01Q86jTk/cXnpOuv2Zve7PW/cn3kMe3Z71XtX
+BzxTfLz97cJUAsUCCIGfQ1+GdIfWht2JDwywi5SKYotap30Ironpjo2I84/3iRBPJE8cTFpKLlh
b8m+9P3xB6JSSKlJaTkHz6R3Zrw8RJalnh2ZU507cYQ8Tz0/7GhFwXDhxrFdx92Kc040l0yVUpQp
lHucyq5orHx6BlMlUe149sC5C+dHa1ZreS6a1+291Hj5Y71qQ/7VD9fcrt9vtmp52KbeHnOjtuNZ
F0W3XI/jzajejFsFt4v7ivsL7mTdPThw6N6RwSNDGX/FDDvdl7y/NtIzmjymOPb1waOHbeOlE/se
eTzWfSI4STb57unos6bnpS/2vfSc0p8WnaGZ+T77+tXE3MDrm/M33rQttC2ee5u3FPfO/b3BB/Fl
muWVj5Ofuj6f+ZKxEvjV7JvUKv3qt+/PfvSsVa2nb/j91N/k29xE448DbOjtMAH0oTc6c+go9BKW
Q+9enxEPZAK9NT3HRuKIuBa8H4GNMElWTh5AoUupQWVPDKROoTlNe5NugYGRUZ8pkbme5QObJDuJ
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
UccrJXgm5ia1Js/vY95vcmBfSmPq4kH+9D0ZpZmPs5izXXIqcl8dkchLyO8vYCmMKBo6Ll1cVkI8
mV1GWX68QrjyzpmgasqzjeddL2BqG+o8LtNcudWQ0Ch17U1TTUtQm0T7p472rrQe817mW7N9DXf2
DpgOsg6NDDvcnx1NesD1cHgi97HdpNAz6PnMy/7putn8OdK83QL7YuWS8LurHzSXhz95fP6wkvKN
evXkD661yg22n/nb8WcGOiASVIL7YBONvT90EuqDPsN8sC2cDrfASwgv4oyu9wEMgtHEJGFaMCtY
BWwcthOHxVnhynCLeDX8Ufwbgj7hLBmBLJLsGbk5eQ+FEhppXcohKheqReJ+akbqBhormo+0xXSa
dAv0pxjsGKkY7zFlM5uz0LFMsp5jI7HrcNBzvOXs5zrLnckTwmvPp8MvKyAsyC3ELswmwiMqLqYi
brbLS2KvZKlUp/QrWaKcujxJ4YriB2UFlVTVMXURjXTN19rmOi164vpnDXmNqk1ETZvM9S0eW0Xa
UNo22Luh67XTJc5Nfveqe4/nEW93X0V/yoAnQaUhJqEL4YkR61ExpLkY69hr8bQJpMSHyap7z+yn
OJCQMp/mfHAoQzezPUs+uzlX4/BAnkv+24L9RbTHqoqlTrSd1CztLlc/1VyJPW1+5njVy7Ni5+LP
911grPW/2H6JeNn3SkcD49XIxsHrImjm867Vpq3lBldHZuf7bqeem73it47f3uwPvvNwQPte3RDT
X9HD90bYRwPHLj1YHOefcHqU9vjCk3uTc0/Xn9O84H4pPqUwrTqjOav9SntO87XqvNIbmQWxRb63
xLcLS23v4t8rvF/6cG7Z5SP5x45P/p9pPrd+2b0CVqq+6n6d+XZglWO17bvD9+Ufh9eE13rX3ddX
N4p+Sv0c2PTdin+0v5zs9vEBUeoCgH2xuflZCE0qCgHYKNjcXKva3NyoRpONZwD0hO78t7N91tAA
UF79n/5j+S+y5M7QfRndOAAAAZtpVFh0WE1MOmNvbS5hZG9iZS54bXAAAAAAADx4OnhtcG1ldGEg
eG1sbnM6eD0iYWRvYmU6bnM6bWV0YS8iIHg6eG1wdGs9IlhNUCBDb3JlIDUuNC4wIj4KICAgPHJk
ZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgt
bnMjIj4KICAgICAgPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIKICAgICAgICAgICAgeG1s
bnM6ZXhpZj0iaHR0cDovL25zLmFkb2JlLmNvbS9leGlmLzEuMC8iPgogICAgICAgICA8ZXhpZjpQ
aXhlbFhEaW1lbnNpb24+Njg8L2V4aWY6UGl4ZWxYRGltZW5zaW9uPgogICAgICAgICA8ZXhpZjpQ
aXhlbFlEaW1lbnNpb24+Mjk8L2V4aWY6UGl4ZWxZRGltZW5zaW9uPgogICAgICA8L3JkZjpEZXNj
cmlwdGlvbj4KICAgPC9yZGY6UkRGPgo8L3g6eG1wbWV0YT4K1c8BZQAABrFJREFUWAntWHtsU1UY
/7oHuxp1FyOxRsPaGJJh1HWJCZrMtUQTlqjJIsqtRGmnCfIIdvIa/mEI/IEPkC1RWKcJK0TpRniI
JGxEZGwQRtDQTsVWUHvlD1aH2pKAPRPp8Tvn9t7eR8tm4A/AneT2vH7fd77zO4/vO7VRTDCRNAZK
tNJEgTMwQYhpI0wQMkGIiQFTdWKH3DKEkDPQbCuH0tplIJP/7ijlPavBZrPBqr0/GSi5qXdIFP6B
bPQEpA1TGl+FkPMcKKczBoEyQ+1mqggiNLe3gVeYBg7Bdt0sL04IIZBMJoHAKH53gcNxHwhXGZak
f4MkY1uoBLt9cnEsuYB6U0AEAURRBBHzYomQEZDlP3m3YK8Ch3ibDjoFGhcEdHV9cRTSaHuaHaWx
7NGLsTKLVM0p1vMRO5Smr46GI79r0MTuVbxfav2Mdq6cZcDaahbTvsQlDasUCB3cssKAY2O4A5/Q
WCZrwfZtnG/B2tzLaCT1l4LNnKY+KKElJYt08oRGtr9tkWPjBNoP0oxulNj2hRwnhb7VtWLUbqhh
JRXZklfofpm2tDTTGh054dxEVYV54uqoJD2Wl4U6Opi6klNP6J43Hsz31bxAfXPy2NLSpYZJ6bE1
0hIa8D2lyZaVraHDTGuOEJttNo3kCE3sf0vDAY4RCASoW2e77/MzOXsoVe0fk5DBdc9wpWWrDmjC
lI7Qzjn383ZPUGFUVcgIkYJHNPYziSOaEa53B7gOPcmtfac0vanITo1sqes73p6J7dIm5Qt9bcCq
5IfjFw2EKDuM0PCTU7isW2cPpYT2bXxWmVPzF5qdqv1jE7LRx4VLvR/ThG4rZxJDNBwO077csVEV
stVNaGYrheFDaxQDXO/RFBoUnvMAr3vaTpiQlKpHr8y7lRvbt86jyPq3acYrQrjL5lXxvtbj5wsQ
QmkkvB53xQZtx6iDJfav5nKTPMoYrF2130yI5VIV7bfjQgBc6ZoPTvxwy4K/wQMez0zweh/lffqf
uk1ecOgbsCw6H+EtV4ZOYIyQAZIkvD6wNAShylNA8MLmCS9UubODF0uSLBsFufd7Xp/tcZku5gpo
3CpDpoOCwLwKSXGc/sflXQ5tjSMQPb4PQvEExONDIEei0D0Q0cOuWrYQUv1SK/SN3gEzm9ZzwaHu
D+FN/FjC8wqHftkGHodCGmuzF/ASgn0aSFACOxiAJXsFz7LZzdDUxIvWnwuMpAqobnwCYGAfuByT
rRhs4WQU7AGIY7A1/fm1RXrH11wgMKsAj/99oJkMJGJR6Al3QKC+lmujdBfMatqJbliXCsQARD4N
3ZBFUAWuMrrA2EUuIIWOQCKRKPj9uP9FjpWPK6sZTVrDLebaZVlW3KnOBF5MHtLIQG8EPYMncZxz
kMlkIRX5zIwuWjcRch6C0tPg8iyHOE7GUV0DDd750NZ/ElLHNnMll/sPGELl3cFjlkgxnfyVY8vd
szBoEsE+/c6cAZUYzzgMn5g+Bn6/H9r2nuIYQSjl+e7eH4zEI7GhyU5wOp0QHPojpy+fkbRCYKlr
LZw7vAEaHq9VYidcsGTkqzxwjJKJEALyjgEY6v8AgjkDVfn0qLIvympm4DHBM5xLlw+/Ds3d36hV
IPGD0DBzKa8/1OjEVa8AV+NzvN7tXwS98Ut5rHwUFtS+Av39/RBFHNtRngUtvP9ySILg4Z81rNy7
CRaCEma7qu7W2vOFUV7MDsUxQGS7U0nJ6C7wvrqFV7J2tfUquXoTq3ls+2v8RkYRChgDtHcGaUAX
M7hzrlC9pTkOsTW+FfSdwFxNVh8fUHqWtkC51icFVhqwxuDqAu2sv0fDun1LDDFLefMBxfuY45DU
Uc2FAzxMAy0tVKqv1PSodvpav+Tyqv1mL2MJzJjf7lk3z6KIKZTaFGV6twXuxTRQLxrwBSPVzFna
Pm+GAcd0lnjWYvSpBnDqsozQsCn6ZVhf6z5047lUIFIdHvzUot/mXU8jsai2IJNqOwyE+HLxj6rW
xgo4mCWR9FmI4ztCwPcDwS1or3YaPEo8vAimz20Hqes0dEnTIMkvO4Je4F48u4U9BBuE4P2ivjBF
exXYDe8Toxn8fUQmgYDvH/aWEXVH1YjU1RAry8P8/jHoR1efZu6evaEKeEZVg8Xtqh2COBVcrqlq
tXieiynseFmO54iyiVWPB4gjCiKSy0cuTrDFMHzMOaorLc1jEaEKmC5Vtfn/m18DIX9z1niAeQvx
V/QOGXuO+D9JGq8fAYOv8ZztsRXeEIhrIOSGsP+6G3ENR+a623JDKJwgxLQM/wKlv4aNE1ZNyAAA
AABJRU5ErkJggg==""")


class TestTeams(Harness):

    valid_data = {
        'name': 'Gratiteam',
        'product_or_service': 'We make widgets.',
        'homepage': 'http://gratipay.com/',
        'onboarding_url': 'http://inside.gratipay.com/',
        'agree_public': 'true',
        'agree_payroll': 'true',
        'agree_terms': 'true',
        'image': FileUpload(IMAGE, 'logo.png'),
    }

    def post_new(self, data, auth_as='alice', expected=200):
        r =  self.client.POST( '/teams/create.json'
                             , data=data
                             , auth_as=auth_as
                             , raise_immediately=False
                              )
        assert r.code == expected
        return r

    def test_harness_can_make_a_team(self):
        team = self.make_team()
        assert team.name == 'The Enterprise'
        assert team.owner == 'picard'

    def test_can_construct_from_slug(self):
        self.make_team()
        team = Team.from_slug('TheEnterprise')
        assert team.name == 'The Enterprise'
        assert team.owner == 'picard'

    def test_can_construct_from_id(self):
        team = Team.from_id(self.make_team().id)
        assert team.name == 'The Enterprise'
        assert team.owner == 'picard'

    @mock.patch('gratipay.models.team.Team.create_github_review_issue')
    def test_can_create_new_team(self, cgri):
        cgri.return_value = REVIEW_URL
        self.make_participant('alice', claimed_time='now', email_address='', last_paypal_result='')
        r = self.post_new(dict(self.valid_data))
        team = self.db.one("SELECT * FROM teams")
        assert team
        assert team.owner == 'alice'
        assert json.loads(r.body)['review_url'] == team.review_url

    def test_all_fields_persist(self):
        self.make_participant('alice', claimed_time='now', email_address='', last_paypal_result='')
        self.post_new(dict(self.valid_data))
        team = T('gratiteam')
        assert team.name == 'Gratiteam'
        assert team.homepage == 'http://gratipay.com/'
        assert team.product_or_service == 'We make widgets.'
        fallback = 'https://github.com/gratipay/team-review/issues#error-401'
        assert team.review_url in (REVIEW_URL, fallback)

    def test_casing_of_urls_survives(self):
        self.make_participant('alice', claimed_time='now', email_address='', last_paypal_result='')
        self.post_new(dict( self.valid_data
                          , homepage='Http://gratipay.com/'
                           ))
        team = T('gratiteam')
        assert team.homepage == 'Http://gratipay.com/'

    def test_casing_of_slug_survives(self):
        self.make_participant('alice', claimed_time='now', email_address='', last_paypal_result='')
        data = dict(self.valid_data)
        data['name'] = 'GratiTeam'
        self.post_new(dict(data))
        team = T('GratiTeam')
        assert team is not None
        assert team.slug_lower == 'gratiteam'

    def test_401_for_anon_creating_new_team(self):
        self.post_new(self.valid_data, auth_as=None, expected=401)
        assert self.db.one("SELECT COUNT(*) FROM teams") == 0

    def test_error_message_for_no_valid_email(self):
        self.make_participant('alice', claimed_time='now')
        r = self.post_new(dict(self.valid_data), expected=400)
        assert self.db.one("SELECT COUNT(*) FROM teams") == 0
        assert "You must have a verified email address to apply for a new team." in r.body

    def test_error_message_for_no_payout_route(self):
        self.make_participant('alice', claimed_time='now', email_address='alice@example.com')
        r = self.post_new(dict(self.valid_data), expected=400)
        assert self.db.one("SELECT COUNT(*) FROM teams") == 0
        assert "You must attach a PayPal account to apply for a new team." in r.body

    def test_error_message_for_public_review(self):
        self.make_participant('alice', claimed_time='now', email_address='alice@example.com', last_paypal_result='')
        data = dict(self.valid_data)
        del data['agree_public']
        r = self.post_new(data, expected=400)
        assert self.db.one("SELECT COUNT(*) FROM teams") == 0
        assert "Sorry, you must agree to have your application publicly reviewed." in r.body

    def test_error_message_for_terms(self):
        self.make_participant('alice', claimed_time='now', email_address='alice@example.com', last_paypal_result='')
        data = dict(self.valid_data)
        del data['agree_terms']
        r = self.post_new(data, expected=400)
        assert self.db.one("SELECT COUNT(*) FROM teams") == 0
        assert "Sorry, you must agree to the terms of service." in r.body

    def test_error_message_for_missing_fields(self):
        self.make_participant('alice', claimed_time='now', email_address='alice@example.com', last_paypal_result='')
        data = dict(self.valid_data)
        del data['name']
        r = self.post_new(data, expected=400)
        assert self.db.one("SELECT COUNT(*) FROM teams") == 0
        assert "Please fill out the 'Team Name' field." in r.body

    def test_error_message_for_bad_url(self):
        self.make_participant('alice', claimed_time='now', email_address='alice@example.com', last_paypal_result='')

        r = self.post_new(dict(self.valid_data, homepage='foo'), expected=400)
        assert self.db.one("SELECT COUNT(*) FROM teams") == 0
        assert "Please enter an http[s]:// URL for the 'Homepage' field." in r.body

    def test_error_message_for_invalid_team_name(self):
        self.make_participant('alice', claimed_time='now', email_address='alice@example.com', last_paypal_result='')
        data = dict(self.valid_data)
        data['name'] = '~Invalid:Name;'
        r = self.post_new(data, expected=400)
        assert self.db.one("SELECT COUNT(*) FROM teams") == 0
        assert "Sorry, your team name is invalid." in r.body

    def test_error_message_for_slug_collision(self):
        self.make_participant('alice', claimed_time='now', email_address='alice@example.com', last_paypal_result='')
        self.post_new(dict(self.valid_data))
        r = self.post_new(dict(self.valid_data), expected=400)
        assert self.db.one("SELECT COUNT(*) FROM teams") == 1
        assert "Sorry, there is already a team using 'Gratiteam'." in r.body

    def test_approved_team_shows_up_on_homepage(self):
        self.make_team(is_approved=True)
        assert 'The Enterprise' in self.client.GET("/").body

    def test_unreviewed_team_shows_up_on_homepage(self):
        self.make_team(is_approved=None)
        assert 'The Enterprise' in self.client.GET("/").body

    def test_rejected_team_shows_up_on_homepage(self):
        self.make_team(is_approved=False)
        assert 'The Enterprise' in self.client.GET("/").body

    def test_stripping_required_inputs(self):
        self.make_participant('alice', claimed_time='now', email_address='alice@example.com', last_paypal_result='')
        data = dict(self.valid_data)
        data['name'] = "     "
        r = self.post_new(data, expected=400)
        assert self.db.one("SELECT COUNT(*) FROM teams") == 0
        assert "Please fill out the 'Team Name' field." in r.body

    def test_receiving_page_basically_works(self):
        team = self.make_team(is_approved=True)
        alice = self.make_participant('alice', claimed_time='now', last_bill_result='')
        alice.set_payment_instruction(team, '3.00')
        body = self.client.GET('/TheEnterprise/receiving/', auth_as='picard').body
        assert '100.0%' in body


    # Dues, Upcoming Payment
    # ======================

    def test_get_dues(self):
        alice = self.make_participant('alice', claimed_time='now', last_bill_result='')
        bob = self.make_participant('bob', claimed_time='now', last_bill_result='Fail!')
        team = self.make_team(is_approved=True)

        alice.set_payment_instruction(team, '3.00') # Funded
        bob.set_payment_instruction(team, '5.00') # Unfunded

        # Simulate dues
        self.db.run("UPDATE payment_instructions SET due = amount")

        assert team.get_dues() == (3, 5)


    def test_upcoming_payment(self):
        alice = self.make_participant('alice', claimed_time='now', last_bill_result='')
        bob = self.make_participant('bob', claimed_time='now', last_bill_result='')
        carl = self.make_participant('carl', claimed_time='now', last_bill_result='Fail!')
        team = self.make_team(is_approved=True)

        alice.set_payment_instruction(team, '5.00') # Funded
        bob.set_payment_instruction(team, '3.00') # Funded, but won't hit minimum charge
        carl.set_payment_instruction(team, '10.00') # Unfunded

        # Simulate dues
        self.db.run("UPDATE payment_instructions SET due = amount")

        assert team.get_upcoming_payment() == 10 # 2 * Alice's $5

    # Cached Values
    # =============

    def test_receiving_only_includes_funded_payment_instructions(self):
        alice = self.make_participant('alice', claimed_time='now', last_bill_result='')
        bob = self.make_participant('bob', claimed_time='now', last_bill_result="Fail!")
        team = self.make_team(is_approved=True)

        alice.set_payment_instruction(team, '3.00') # The only funded payment instruction
        bob.set_payment_instruction(team, '5.00')

        assert team.receiving == D('3.00')
        assert team.nreceiving_from == 1

        funded_payment_instruction = self.db.one("SELECT * FROM payment_instructions "
                                                 "WHERE is_funded ORDER BY id")
        assert funded_payment_instruction.participant_id == alice.id

    def test_receiving_only_includes_latest_payment_instructions(self):
        alice = self.make_participant('alice', claimed_time='now', last_bill_result='')
        team = self.make_team(is_approved=True)

        alice.set_payment_instruction(team, '5.00')
        alice.set_payment_instruction(team, '3.00')

        assert team.receiving == D('3.00')
        assert team.nreceiving_from == 1


    # Images
    # ======

    def test_save_image_saves_image(self):
        team = self.make_team()
        team.save_image(IMAGE, IMAGE, IMAGE, 'image/png')
        media_type = self.db.one('SELECT image_type FROM teams WHERE id=%s', (team.id,))
        assert media_type == 'image/png'

    def test_save_image_records_the_event(self):
        team = self.make_team()
        oids = team.save_image(IMAGE, IMAGE, IMAGE, 'image/png')
        event = self.db.all('SELECT * FROM events ORDER BY ts DESC')[0]
        assert event.payload == { 'action': 'upsert_image'
                                , 'original': oids['original']
                                , 'large': oids['large']
                                , 'small': oids['small']
                                , 'id': team.id
                                 }

    def test_load_image_loads_image(self):
        team = self.make_team()
        team.save_image(IMAGE, IMAGE, IMAGE, 'image/png')
        image = team.load_image('large')  # buffer
        assert str(image) == IMAGE

    def test_image_endpoint_serves_an_image(self):
        team = self.make_team()
        team.save_image(IMAGE, IMAGE, IMAGE, 'image/png')
        image = self.client.GET('/TheEnterprise/image').body  # buffer
        assert str(image) == IMAGE


    # Update
    # ======

    def test_update_works(self):
        team = self.make_team(slug='enterprise')
        update_data = {
            'name': 'Enterprise',
            'product_or_service': 'We save galaxies.',
            'homepage': 'http://starwars-enterprise.com/',
            'onboarding_url': 'http://starwars-enterprise.com/onboarding',
        }
        team.update(**update_data)
        team = T('enterprise')
        for field in update_data:
            assert getattr(team, field) == update_data[field]

    def test_can_only_update_allowed_fields(self):
        allowed_fields = set(['name', 'product_or_service', 'homepage',
                              'onboarding_url',])

        team = self.make_team(slug='enterprise')

        fields = vars(team).keys()
        for field in fields:
            if field not in allowed_fields:
                with pytest.raises(AssertionError):
                    team.update(field='foo')

    def test_update_records_the_old_values_as_events(self):
        team = self.make_team(slug='enterprise', product_or_service='Product')
        team.update(name='Enterprise', product_or_service='We save galaxies.')
        event = self.db.all('SELECT * FROM events ORDER BY ts DESC')[0]
        assert event.payload == { 'action': 'update'
                                , 'id': team.id
                                , 'name': 'The Enterprise'
                                , 'product_or_service': 'Product'
                                 }

    def test_update_updates_object_attributes(self):
        team = self.make_team(slug='enterprise')
        team.update(name='Enterprise', product_or_service='We save galaxies.')
        assert team.name == 'Enterprise'
        assert team.product_or_service == 'We save galaxies.'


    # slugize

    def test_slugize_slugizes(self):
        assert slugize('Foo') == 'Foo'

    def test_slugize_requires_a_letter(self):
        assert pytest.raises(InvalidTeamName, slugize, '123')

    def test_slugize_accepts_letter_in_middle(self):
        assert slugize('1a23') == '1a23'

    def test_slugize_converts_comma_to_dash(self):
        assert slugize('foo,bar') == 'foo-bar'

    def test_slugize_converts_space_to_dash(self):
        assert slugize('foo bar') == 'foo-bar'

    def test_slugize_allows_underscore(self):
        assert slugize('foo_bar') == 'foo_bar'

    def test_slugize_allows_period(self):
        assert slugize('foo.bar') == 'foo.bar'

    def test_slugize_trims_whitespace(self):
        assert slugize('  Foo Bar  ') == 'Foo-Bar'

    def test_slugize_trims_dashes(self):
        assert slugize('--Foo Bar--') == 'Foo-Bar'

    def test_slugize_trims_replacement_dashes(self):
        assert slugize(',,Foo Bar,,') == 'Foo-Bar'

    def test_slugize_folds_dashes_together(self):
        assert slugize('1a----------------23') == '1a-23'
