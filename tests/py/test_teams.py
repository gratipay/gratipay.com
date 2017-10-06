from __future__ import absolute_import, division, print_function, unicode_literals

import json
import pytest

from aspen.testing.client import FileUpload
from gratipay.testing import Harness, IMAGE, D,T
from gratipay.testing.email import QueuedEmailHarness
from gratipay.models.team import Team, slugize, InvalidTeamName


class TestTeams(QueuedEmailHarness):

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

    def make_alice(self):
        self.make_participant( 'alice'
                             , claimed_time='now'
                             , email_address='alice@example.com'
                             , last_paypal_result=''
                              )

    def test_can_create_new_team(self):
        self.make_alice()
        r = self.post_new(dict(self.valid_data))
        team = self.db.one("SELECT * FROM teams")
        assert team
        assert team.owner == 'alice'
        assert json.loads(r.body)['review_url'] == team.review_url

    def test_all_fields_persist(self):
        self.make_alice()
        self.post_new(dict(self.valid_data))
        team = T('gratiteam')
        assert team.name == 'Gratiteam'
        assert team.homepage == 'http://gratipay.com/'
        assert team.product_or_service == 'We make widgets.'
        assert team.review_url == 'some-github-issue'

    def test_casing_of_urls_survives(self):
        self.make_alice()
        self.post_new(dict( self.valid_data
                          , homepage='Http://gratipay.com/'
                           ))
        team = T('gratiteam')
        assert team.homepage == 'Http://gratipay.com/'

    def test_casing_of_slug_survives(self):
        self.make_alice()
        data = dict(self.valid_data)
        data['name'] = 'GratiTeam'
        self.post_new(dict(data))
        team = T('GratiTeam')
        assert team is not None
        assert team.slug_lower == 'gratiteam'

    def test_application_email_sent_to_owner(self):
        self.make_alice()
        self.post_new(dict(self.valid_data))
        last_email = self.get_last_email()
        self.app.email_queue.flush()
        assert last_email['to'] == 'alice <alice@example.com>'
        expected = "Thanks for applying to use Gratipay!"
        assert expected in last_email['body_text']

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
        self.make_alice()
        data = dict(self.valid_data)
        del data['agree_public']
        r = self.post_new(data, expected=400)
        assert self.db.one("SELECT COUNT(*) FROM teams") == 0
        assert "Sorry, you must agree to have your application publicly reviewed." in r.body

    def test_error_message_for_terms(self):
        self.make_alice()
        data = dict(self.valid_data)
        del data['agree_terms']
        r = self.post_new(data, expected=400)
        assert self.db.one("SELECT COUNT(*) FROM teams") == 0
        assert "Sorry, you must agree to the terms of service." in r.body

    def test_error_message_for_missing_fields(self):
        self.make_alice()
        data = dict(self.valid_data)
        del data['name']
        r = self.post_new(data, expected=400)
        assert self.db.one("SELECT COUNT(*) FROM teams") == 0
        assert "Please fill out the 'Team Name' field." in r.body

    def test_error_message_for_bad_url(self):
        self.make_alice()
        r = self.post_new(dict(self.valid_data, homepage='foo'), expected=400)
        assert self.db.one("SELECT COUNT(*) FROM teams") == 0
        assert "Please enter an http[s]:// URL for the 'Homepage' field." in r.body

    def test_error_message_for_invalid_team_name(self):
        self.make_alice()
        data = dict(self.valid_data)
        data['name'] = '~Invalid:Name;'
        r = self.post_new(data, expected=400)
        assert self.db.one("SELECT COUNT(*) FROM teams") == 0
        assert "Sorry, your team name is invalid." in r.body

    def test_error_message_for_slug_collision(self):
        self.make_alice()
        self.post_new(dict(self.valid_data))
        r = self.post_new(dict(self.valid_data), expected=400)
        assert self.db.one("SELECT COUNT(*) FROM teams") == 1
        assert "Sorry, there is already a team using 'Gratiteam'." in r.body

    def test_stripping_required_inputs(self):
        self.make_alice()
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
        assert event.type == 'team'
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

    def test_get_image_url_gets_image_url(self):
        team = self.make_team()
        team.save_image(IMAGE, IMAGE, IMAGE, 'image/png')
        assert team.get_image_url('small') == '/TheEnterprise/image?size=small'


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

    def test_homepage_not_allowed_for_package(self):
        alice = self.make_participant('alice', claimed_time='now')
        package = self.make_package(name='enterprise')
        with self.db.get_cursor() as c:
            team = package.get_or_create_linked_team(c, alice)
        pytest.raises(AssertionError, team.update, homepage='foo')

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

    def test_slugize_disallows_slashes(self):
        self.assertRaises(InvalidTeamName, slugize, 'abc/def')

    def test_slugize_disallows_questions(self):
        self.assertRaises(InvalidTeamName, slugize, 'abc?def')

    def test_slugize_disallows_backslashes(self):
        self.assertRaises(InvalidTeamName, slugize, 'abc\def')


class Cast(Harness):

    def test_casts_team(self):
        team = self.make_team()
        state = self.client.GET('/TheEnterprise/', return_after='cast', want='state')
        assert state['request'].path['team'] == team

    def test_canonicalizes(self):
        self.make_team()
        response = self.client.GxT('/theenterprise/', return_after='cast')
        assert response.code == 302
        assert response.headers['Location'] == '/TheEnterprise/'
