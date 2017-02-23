from __future__ import absolute_import, division, print_function, unicode_literals

from cryptography.fernet import InvalidToken
from gratipay.testing import Harness, P
from gratipay.models.participant import identity
from gratipay.models.participant.identity import _validate_info, rekey
from gratipay.models.participant.identity import ParticipantIdentityInfoInvalid
from gratipay.models.participant.identity import ParticipantIdentitySchemaUnknown
from gratipay.security.crypto import EncryptingPacker, Fernet
from postgres.orm import ReadOnly
from psycopg2 import IntegrityError
from pytest import raises


class Tests(Harness):

    @classmethod
    def setUpClass(cls):
        Harness.setUpClass()
        cls.TT = cls.db.one("SELECT id FROM countries WHERE code='TT'")
        cls.US = cls.db.one("SELECT id FROM countries WHERE code='US'")

        def _failer(info):
            raise ParticipantIdentityInfoInvalid('You failed.')
        identity.schema_validators['impossible'] = _failer

    @classmethod
    def tearDownClass(cls):
        del identity.schema_validators['impossible']

    def setUp(self):
        self.crusher = self.make_participant('crusher', email_address='foo@example.com')

    def assert_events(self, crusher_id, identity_ids, country_ids, actions):
        events = self.db.all("SELECT * FROM events ORDER BY ts ASC")
        nevents = len(events)

        assert [e.type for e in events] == ['participant'] * nevents
        assert [e.payload['id'] for e in events] == [crusher_id] * nevents
        assert [e.payload['identity_id'] for e in events] == identity_ids
        assert [e.payload['country_id'] for e in events] == country_ids
        assert [e.payload['action'] for e in events] == actions


    # rii - retrieve_identity_info

    def test_rii_retrieves_identity_info(self):
        self.crusher.store_identity_info(self.US, 'nothing-enforced', {'name': 'Crusher'})
        assert self.crusher.retrieve_identity_info(self.US)['name'] == 'Crusher'

    def test_rii_retrieves_identity_when_there_are_multiple_identities(self):
        self.crusher.store_identity_info(self.US, 'nothing-enforced', {'name': 'Crusher'})
        self.crusher.store_identity_info(self.TT, 'nothing-enforced', {'name': 'Bruiser'})
        assert self.crusher.retrieve_identity_info(self.US)['name'] == 'Crusher'
        assert self.crusher.retrieve_identity_info(self.TT)['name'] == 'Bruiser'

    def test_rii_returns_None_if_there_is_no_identity_info(self):
        assert self.crusher.retrieve_identity_info(self.US) is None

    def test_rii_logs_event(self):
        iid = self.crusher.store_identity_info(self.TT, 'nothing-enforced', {'name': 'Crusher'})
        self.crusher.retrieve_identity_info(self.TT)
        self.assert_events( self.crusher.id
                          , [iid, iid]
                          , [self.TT, self.TT]
                          , ['insert identity', 'retrieve identity']
                           )

    def test_rii_still_logs_an_event_when_noop(self):
        self.crusher.retrieve_identity_info(self.TT)
        self.assert_events( self.crusher.id
                          , [None]
                          , [self.TT]
                          , ['retrieve identity']
                           )


    # lim - list_identity_metadata

    def test_lim_lists_identity_metadata(self):
        self.crusher.store_identity_info(self.US, 'nothing-enforced', {'name': 'Crusher'})
        assert [x.country.code for x in self.crusher.list_identity_metadata()] == ['US']

    def test_lim_lists_the_latest_identity_metadata(self):
        self.crusher.store_identity_info(self.US, 'nothing-enforced', {'name': 'Crusher'})
        self.crusher.set_identity_verification(self.US, True)
        self.crusher.store_identity_info(self.US, 'nothing-enforced', {'name': 'Bruiser'})
        assert [x.is_verified for x in self.crusher.list_identity_metadata()] == [False]

    def test_lim_lists_metadata_for_multiple_identities(self):
        for country in (self.US, self.TT):
            self.crusher.store_identity_info(country, 'nothing-enforced', {'name': 'Crusher'})
        assert [x.country.code for x in self.crusher.list_identity_metadata()] == ['TT', 'US']

    def test_lim_lists_latest_metadata_for_multiple_identities(self):
        for country_id in (self.US, self.TT):
            self.crusher.store_identity_info(country_id, 'nothing-enforced', {'name': 'Crusher'})
            self.crusher.set_identity_verification(country_id, True)
            self.crusher.store_identity_info(country_id, 'nothing-enforced', {'name': 'Bruiser'})
        ids = self.crusher.list_identity_metadata()
        assert [x.country.code for x in ids] == ['TT', 'US']
        assert [x.is_verified for x in ids] == [False, False]

    def test_lim_can_filter_on_is_verified(self):
        for country_id in (self.US, self.TT):
            self.crusher.store_identity_info(country_id, 'nothing-enforced', {'name': 'Crusher'})
        self.crusher.set_identity_verification(self.TT, True)

        ids = self.crusher.list_identity_metadata(is_verified=True)
        assert [x.country.code for x in ids] == ['TT']

        ids = self.crusher.list_identity_metadata(is_verified=False)
        assert [x.country.code for x in ids] == ['US']


    # sii - store_identity_info

    def test_sii_sets_identity_info(self):
        self.crusher.store_identity_info(self.TT, 'nothing-enforced', {'name': 'Crusher'})
        assert [x.country.code for x in self.crusher.list_identity_metadata()] == ['TT']

    def test_sii_sets_a_second_identity(self):
        self.crusher.store_identity_info(self.TT, 'nothing-enforced', {'name': 'Crusher'})
        self.crusher.store_identity_info(self.US, 'nothing-enforced', {'name': 'Crusher'})
        assert [x.country.code for x in self.crusher.list_identity_metadata()] == ['TT', 'US']

    def test_sii_overwrites_first_identity(self):
        self.crusher.store_identity_info(self.TT, 'nothing-enforced', {'name': 'Crusher'})
        self.crusher.store_identity_info(self.TT, 'nothing-enforced', {'name': 'Bruiser'})
        assert [x.country.code for x in self.crusher.list_identity_metadata()] == ['TT']
        assert self.crusher.retrieve_identity_info(self.TT)['name'] == 'Bruiser'

    def test_sii_resets_is_verified(self):
        check = lambda: [x.is_verified for x in self.crusher.list_identity_metadata()]
        self.crusher.store_identity_info(self.TT, 'nothing-enforced', {'name': 'Crusher'})
        assert check() == [False]
        self.crusher.set_identity_verification(self.TT, True)
        assert check() == [True]
        self.crusher.store_identity_info(self.TT, 'nothing-enforced', {'name': 'Bruiser'})
        assert check() == [False]

    def test_sii_validates_identity(self):
        raises( ParticipantIdentityInfoInvalid
              , self.crusher.store_identity_info
              , self.TT
              , 'impossible'
              , {'foo': 'bar'}
               )

    def test_sii_happily_overwrites_schema_name(self):
        packed = identity.Identity.encrypting_packer.pack({'name': 'Crusher'})
        self.db.run( "INSERT INTO participant_identities "
                     "(participant_id, country_id, schema_name, info) "
                     "VALUES (%s, %s, %s, %s)"
                   , (self.crusher.id, self.TT, 'flah', packed)
                    )
        assert [x.schema_name for x in self.crusher.list_identity_metadata()] == ['flah']
        self.crusher.store_identity_info(self.TT, 'nothing-enforced', {'name': 'Crusher'})
        assert [x.schema_name for x in self.crusher.list_identity_metadata()] == \
                                                                               ['nothing-enforced']

    def test_sii_logs_event(self):
        iid = self.crusher.store_identity_info(self.TT, 'nothing-enforced', {'name': 'Crusher'})
        self.assert_events(self.crusher.id, [iid], [self.TT], ['insert identity'])


    # _vi - _validate_info

    def test__vi_validates_info(self):
        err = raises(ParticipantIdentityInfoInvalid, _validate_info, 'impossible', {'foo': 'bar'})
        assert err.value.message == 'You failed.'

    def test__vi_chokes_on_unknown_schema(self):
        err = raises(ParticipantIdentitySchemaUnknown, _validate_info, 'floo-floo', {'foo': 'bar'})
        assert err.value.message == "unknown schema 'floo-floo'"


    # siv - set_identity_verification

    def test_is_verified_defaults_to_false(self):
        self.crusher.store_identity_info(self.TT, 'nothing-enforced', {'name': 'Crusher'})
        assert [x.is_verified for x in self.crusher.list_identity_metadata()] == [False]

    def test_siv_sets_identity_verification(self):
        self.crusher.store_identity_info(self.TT, 'nothing-enforced', {'name': 'Crusher'})
        self.crusher.set_identity_verification(self.TT, True)
        assert [x.is_verified for x in self.crusher.list_identity_metadata()] == [True]

    def test_siv_can_set_identity_verification_back_to_false(self):
        self.crusher.store_identity_info(self.TT, 'nothing-enforced', {'name': 'Crusher'})
        self.crusher.set_identity_verification(self.TT, True)
        self.crusher.set_identity_verification(self.TT, False)
        assert [x.is_verified for x in self.crusher.list_identity_metadata()] == [False]

    def test_siv_is_a_noop_when_there_is_no_identity(self):
        assert self.crusher.set_identity_verification(self.TT, True) is None
        assert self.crusher.set_identity_verification(self.TT, False) is None
        assert [x.is_verified for x in self.crusher.list_identity_metadata()] == []

    def test_siv_logs_event_when_successful(self):
        iid = self.crusher.store_identity_info(self.TT, 'nothing-enforced', {'name': 'Crusher'})
        self.crusher.set_identity_verification(self.TT, True) is None
        self.assert_events( self.crusher.id
                          , [iid, iid]
                          , [self.TT, self.TT]
                          , ['insert identity', 'verify identity']
                           )

    def test_siv_logs_event_when_set_to_false(self):
        iid = self.crusher.store_identity_info(self.TT, 'nothing-enforced', {'name': 'Crusher'})
        self.crusher.set_identity_verification(self.TT, True) is None
        self.crusher.set_identity_verification(self.TT, False) is None
        self.assert_events( self.crusher.id
                          , [iid, iid, iid]
                          , [self.TT, self.TT, self.TT]
                          , ['insert identity', 'verify identity', 'unverify identity']
                           )

    def test_siv_still_logs_an_event_when_noop(self):
        self.crusher.set_identity_verification(self.TT, True)
        self.crusher.set_identity_verification(self.TT, False)
        self.assert_events( self.crusher.id
                          , [None, None]
                          , [self.TT, self.TT]
                          , ['verify identity', 'unverify identity']
                           )


    # ci - clear_identity

    def test_ci_clears_identity(self):
        self.crusher.store_identity_info(self.TT, 'nothing-enforced', {'name': 'Crusher'})
        assert self.crusher.clear_identity(self.TT) is None
        assert self.crusher.list_identity_metadata() == []

    def test_ci_is_a_noop_when_there_is_no_identity(self):
        assert self.crusher.clear_identity(self.TT) is None
        assert self.crusher.list_identity_metadata() == []

    def test_ci_logs_an_event(self):
        iid = self.crusher.store_identity_info(self.TT, 'nothing-enforced', {'name': 'Crusher'})
        self.crusher.clear_identity(self.TT)
        self.assert_events( self.crusher.id
                          , [iid, iid]
                          , [self.TT, self.TT]
                          , ['insert identity', 'clear identity']
                           )

    def test_ci_still_logs_an_event_when_noop(self):
        self.crusher.clear_identity(self.TT)
        self.assert_events(self.crusher.id, [None], [self.TT], ['clear identity'])


    # hvi - has_verified_identity

    def test_hvi_defaults_to_false(self):
        assert self.crusher.has_verified_identity is False

    def test_hvi_is_read_only(self):
        with raises(ReadOnly):
            self.crusher.has_verified_identity = True

    def test_hvi_becomes_true_when_an_identity_is_verified(self):
        self.crusher.store_identity_info(self.TT, 'nothing-enforced', {})
        self.crusher.set_identity_verification(self.TT, True)
        assert self.crusher.has_verified_identity
        assert P('crusher').has_verified_identity

    def test_hvi_becomes_false_when_the_identity_is_unverified(self):
        self.crusher.store_identity_info(self.TT, 'nothing-enforced', {})
        self.crusher.set_identity_verification(self.TT, True)
        self.crusher.set_identity_verification(self.TT, False)
        assert not self.crusher.has_verified_identity
        assert not P('crusher').has_verified_identity

    def test_hvi_stays_true_when_a_secondary_identity_is_verified(self):
        self.crusher.store_identity_info(self.US, 'nothing-enforced', {})
        self.crusher.set_identity_verification(self.US, True)
        self.crusher.store_identity_info(self.TT, 'nothing-enforced', {})
        self.crusher.set_identity_verification(self.TT, True)
        assert self.crusher.has_verified_identity
        assert P('crusher').has_verified_identity

    def test_hvi_stays_true_when_the_secondary_identity_is_unverified(self):
        self.crusher.store_identity_info(self.US, 'nothing-enforced', {})
        self.crusher.set_identity_verification(self.US, True)
        self.crusher.store_identity_info(self.TT, 'nothing-enforced', {})
        self.crusher.set_identity_verification(self.TT, True)
        self.crusher.set_identity_verification(self.TT, False)
        assert self.crusher.has_verified_identity
        assert P('crusher').has_verified_identity

    def test_hvi_goes_back_to_false_when_both_are_unverified(self):
        self.crusher.store_identity_info(self.US, 'nothing-enforced', {})
        self.crusher.store_identity_info(self.TT, 'nothing-enforced', {})
        self.crusher.set_identity_verification(self.TT, True)
        self.crusher.set_identity_verification(self.US, True)
        self.crusher.set_identity_verification(self.TT, False)
        self.crusher.set_identity_verification(self.US, False)
        assert not self.crusher.has_verified_identity
        assert not P('crusher').has_verified_identity

    def test_hvi_changes_are_scoped_to_a_participant(self):
        self.crusher.store_identity_info(self.US, 'nothing-enforced', {})

        bruiser = self.make_participant('bruiser', email_address='bruiser@example.com')
        bruiser.store_identity_info(self.US, 'nothing-enforced', {})

        self.crusher.set_identity_verification(self.US, True)

        assert self.crusher.has_verified_identity
        assert P('crusher').has_verified_identity
        assert not bruiser.has_verified_identity
        assert not P('bruiser').has_verified_identity

    def test_hvi_resets_when_identity_is_cleared(self):
        self.crusher.store_identity_info(self.TT, 'nothing-enforced', {})
        self.crusher.set_identity_verification(self.TT, True)
        self.crusher.clear_identity(self.TT)
        assert not self.crusher.has_verified_identity
        assert not P('crusher').has_verified_identity

    def test_hvi_doesnt_reset_when_penultimate_identity_is_cleared(self):
        self.crusher.store_identity_info(self.US, 'nothing-enforced', {})
        self.crusher.set_identity_verification(self.US, True)
        self.crusher.store_identity_info(self.TT, 'nothing-enforced', {})
        self.crusher.set_identity_verification(self.TT, True)
        self.crusher.set_identity_verification(self.TT, False)
        self.crusher.clear_identity(self.TT)
        assert self.crusher.has_verified_identity
        assert P('crusher').has_verified_identity

    def test_hvi_does_reset_when_both_identities_are_cleared(self):
        self.crusher.store_identity_info(self.US, 'nothing-enforced', {})
        self.crusher.store_identity_info(self.TT, 'nothing-enforced', {})
        self.crusher.set_identity_verification(self.US, True)
        self.crusher.set_identity_verification(self.TT, True)
        self.crusher.set_identity_verification(self.TT, False)
        self.crusher.set_identity_verification(self.US, False)
        self.crusher.clear_identity(self.TT)
        assert not self.crusher.has_verified_identity
        assert not P('crusher').has_verified_identity


    # fine - fail_if_no_email

    def test_fine_fails_if_no_email(self):
        bruiser = self.make_participant('bruiser')
        error = raises( IntegrityError
                      , bruiser.store_identity_info
                      , self.US
                      , 'nothing-enforced'
                      , {'name': 'Bruiser'}
                       ).value
        assert error.pgcode == '23100'
        assert bruiser.list_identity_metadata() == []


    # rekey

    def rekey_setup(self):
        self.crusher.store_identity_info(self.US, 'nothing-enforced', {'name': 'Crusher'})
        self.db.run("UPDATE participant_identities "
                    "SET _info_last_keyed=_info_last_keyed - '6 months'::interval")
        old_key = str(self.client.website.env.crypto_keys)
        return EncryptingPacker(Fernet.generate_key(), old_key)

    def test_rekey_rekeys(self):
        assert rekey(self.db, self.rekey_setup()) == 1

    def test_rekeying_causes_old_packer_to_fail(self):
        rekey(self.db, self.rekey_setup())
        raises(InvalidToken, self.crusher.retrieve_identity_info, self.US)

    def test_rekeyed_data_is_accessible_with_new_key(self):
        self.crusher.encrypting_packer = self.rekey_setup()
        assert self.crusher.retrieve_identity_info(self.US) == {'name': 'Crusher'}

    def test_rekey_ignores_recently_keyed_records(self):
        self.crusher.encrypting_packer = self.rekey_setup()
        assert rekey(self.db, self.crusher.encrypting_packer) == 1
        assert rekey(self.db, self.crusher.encrypting_packer) == 0
