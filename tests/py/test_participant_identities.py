from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing import Harness
from gratipay.models.participant import Participant
from gratipay.models.participant.mixins import identity, Identity
from gratipay.models.participant.mixins.identity import _validate_info
from gratipay.models.participant.mixins.identity import ParticipantIdentityInfoInvalid
from gratipay.models.participant.mixins.identity import ParticipantIdentitySchemaUnknown
from postgres.orm import ReadOnly
from pytest import raises


class Tests(Harness):

    @classmethod
    def setUpClass(cls):
        Harness.setUpClass()
        cls.TTO = cls.db.one("SELECT id FROM countries WHERE code3='TTO'")
        cls.USA = cls.db.one("SELECT id FROM countries WHERE code3='USA'")

        def _failer(info):
            raise ParticipantIdentityInfoInvalid('You failed.')
        identity.schema_validators['impossible'] = _failer

    @classmethod
    def tearDownClass(cls):
        del identity.schema_validators['impossible']

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
        crusher = self.make_participant('crusher')
        crusher.store_identity_info(self.USA, 'nothing-enforced', {'name': 'Crusher'})
        assert crusher.retrieve_identity_info(self.USA)['name'] == 'Crusher'

    def test_rii_retrieves_identity_when_there_are_multiple_identities(self):
        crusher = self.make_participant('crusher')
        crusher.store_identity_info(self.USA, 'nothing-enforced', {'name': 'Crusher'})
        crusher.store_identity_info(self.TTO, 'nothing-enforced', {'name': 'Bruiser'})
        assert crusher.retrieve_identity_info(self.USA)['name'] == 'Crusher'
        assert crusher.retrieve_identity_info(self.TTO)['name'] == 'Bruiser'

    def test_rii_returns_None_if_there_is_no_identity_info(self):
        crusher = self.make_participant('crusher')
        assert crusher.retrieve_identity_info(self.USA) is None

    def test_rii_logs_event(self):
        crusher = self.make_participant('crusher')
        iid = crusher.store_identity_info(self.TTO, 'nothing-enforced', {'name': 'Crusher'})
        crusher.retrieve_identity_info(self.TTO)
        self.assert_events( crusher.id
                          , [iid, iid]
                          , [self.TTO, self.TTO]
                          , ['insert identity', 'retrieve identity']
                           )

    def test_rii_still_logs_an_event_when_noop(self):
        crusher = self.make_participant('crusher')
        crusher.retrieve_identity_info(self.TTO)
        self.assert_events( crusher.id
                          , [None]
                          , [self.TTO]
                          , ['retrieve identity']
                           )


    # lim - list_identity_metadata

    def test_lim_lists_identity_metadata(self):
        crusher = self.make_participant('crusher')
        crusher.store_identity_info(self.USA, 'nothing-enforced', {'name': 'Crusher'})
        assert [x.country.code3 for x in crusher.list_identity_metadata()] == ['USA']

    def test_lim_lists_the_latest_identity_metadata(self):
        crusher = self.make_participant('crusher')
        crusher.store_identity_info(self.USA, 'nothing-enforced', {'name': 'Crusher'})
        crusher.set_identity_verification(self.USA, True)
        crusher.store_identity_info(self.USA, 'nothing-enforced', {'name': 'Bruiser'})
        assert [x.is_verified for x in crusher.list_identity_metadata()] == [False]

    def test_lim_lists_metadata_for_multiple_identities(self):
        crusher = self.make_participant('crusher')
        for country in (self.USA, self.TTO):
            crusher.store_identity_info(country, 'nothing-enforced', {'name': 'Crusher'})
        assert [x.country.code3 for x in crusher.list_identity_metadata()] == ['TTO', 'USA']

    def test_lim_lists_latest_metadata_for_multiple_identities(self):
        crusher = self.make_participant('crusher')
        for country_id in (self.USA, self.TTO):
            crusher.store_identity_info(country_id, 'nothing-enforced', {'name': 'Crusher'})
            crusher.set_identity_verification(country_id, True)
            crusher.store_identity_info(country_id, 'nothing-enforced', {'name': 'Bruiser'})
        ids = crusher.list_identity_metadata()
        assert [x.country.code3 for x in ids] == ['TTO', 'USA']
        assert [x.is_verified for x in ids] == [False, False]

    def test_lim_can_filter_on_is_verified(self):
        crusher = self.make_participant('crusher')
        for country_id in (self.USA, self.TTO):
            crusher.store_identity_info(country_id, 'nothing-enforced', {'name': 'Crusher'})
        crusher.set_identity_verification(self.TTO, True)

        ids = crusher.list_identity_metadata(is_verified=True)
        assert [x.country.code3 for x in ids] == ['TTO']

        ids = crusher.list_identity_metadata(is_verified=False)
        assert [x.country.code3 for x in ids] == ['USA']


    # sii - store_identity_info

    def test_sii_sets_identity_info(self):
        crusher = self.make_participant('crusher')
        crusher.store_identity_info(self.TTO, 'nothing-enforced', {'name': 'Crusher'})
        assert [x.country.code3 for x in crusher.list_identity_metadata()] == ['TTO']

    def test_sii_sets_a_second_identity(self):
        crusher = self.make_participant('crusher')
        crusher.store_identity_info(self.TTO, 'nothing-enforced', {'name': 'Crusher'})
        crusher.store_identity_info(self.USA, 'nothing-enforced', {'name': 'Crusher'})
        assert [x.country.code3 for x in crusher.list_identity_metadata()] == ['TTO', 'USA']

    def test_sii_overwrites_first_identity(self):
        crusher = self.make_participant('crusher')
        crusher.store_identity_info(self.TTO, 'nothing-enforced', {'name': 'Crusher'})
        crusher.store_identity_info(self.TTO, 'nothing-enforced', {'name': 'Bruiser'})
        assert [x.country.code3 for x in crusher.list_identity_metadata()] == ['TTO']
        assert crusher.retrieve_identity_info(self.TTO)['name'] == 'Bruiser'

    def test_sii_resets_is_verified(self):
        crusher = self.make_participant('crusher')
        crusher.store_identity_info(self.TTO, 'nothing-enforced', {'name': 'Crusher'})
        assert [x.is_verified for x in crusher.list_identity_metadata()] == [False]  # starts False
        crusher.set_identity_verification(self.TTO, True)
        assert [x.is_verified for x in crusher.list_identity_metadata()] == [True]   # can be set
        crusher.store_identity_info(self.TTO, 'nothing-enforced', {'name': 'Bruiser'})
        assert [x.is_verified for x in crusher.list_identity_metadata()] == [False]  # is reset

    def test_sii_validates_identity(self):
        crusher = self.make_participant('crusher')
        raises( ParticipantIdentityInfoInvalid
              , crusher.store_identity_info
              , self.TTO
              , 'impossible'
              , {'foo': 'bar'}
               )

    def test_sii_happily_overwrites_schema_name(self):
        crusher = self.make_participant('crusher')
        packed = Identity.encrypting_packer.pack({'name': 'Crusher'})
        self.db.run( "INSERT INTO participant_identities "
                     "(participant_id, country_id, schema_name, info) "
                     "VALUES (%s, %s, %s, %s)"
                   , (crusher.id, self.TTO, 'flah', packed)
                    )
        assert [x.schema_name for x in crusher.list_identity_metadata()] == ['flah']
        crusher.store_identity_info(self.TTO, 'nothing-enforced', {'name': 'Crusher'})
        assert [x.schema_name for x in crusher.list_identity_metadata()] == ['nothing-enforced']

    def test_sii_logs_event(self):
        crusher = self.make_participant('crusher')
        iid = crusher.store_identity_info(self.TTO, 'nothing-enforced', {'name': 'Crusher'})
        self.assert_events(crusher.id, [iid], [self.TTO], ['insert identity'])


    # _vi - _validate_info

    def test__vi_validates_info(self):
        err = raises(ParticipantIdentityInfoInvalid, _validate_info, 'impossible', {'foo': 'bar'})
        assert err.value.message == 'You failed.'

    def test__vi_chokes_on_unknown_schema(self):
        err = raises(ParticipantIdentitySchemaUnknown, _validate_info, 'floo-floo', {'foo': 'bar'})
        assert err.value.message == "unknown schema 'floo-floo'"


    # siv - set_identity_verification

    def test_is_verified_defaults_to_false(self):
        crusher = self.make_participant('crusher')
        crusher.store_identity_info(self.TTO, 'nothing-enforced', {'name': 'Crusher'})
        assert [x.is_verified for x in crusher.list_identity_metadata()] == [False]

    def test_siv_sets_identity_verification(self):
        crusher = self.make_participant('crusher')
        crusher.store_identity_info(self.TTO, 'nothing-enforced', {'name': 'Crusher'})
        crusher.set_identity_verification(self.TTO, True)
        assert [x.is_verified for x in crusher.list_identity_metadata()] == [True]

    def test_siv_can_set_identity_verification_back_to_false(self):
        crusher = self.make_participant('crusher')
        crusher.store_identity_info(self.TTO, 'nothing-enforced', {'name': 'Crusher'})
        crusher.set_identity_verification(self.TTO, True)
        crusher.set_identity_verification(self.TTO, False)
        assert [x.is_verified for x in crusher.list_identity_metadata()] == [False]

    def test_siv_is_a_noop_when_there_is_no_identity(self):
        crusher = self.make_participant('crusher')
        assert crusher.set_identity_verification(self.TTO, True) is None
        assert crusher.set_identity_verification(self.TTO, False) is None
        assert [x.is_verified for x in crusher.list_identity_metadata()] == []

    def test_siv_logs_event_when_successful(self):
        crusher = self.make_participant('crusher')
        iid = crusher.store_identity_info(self.TTO, 'nothing-enforced', {'name': 'Crusher'})
        crusher.set_identity_verification(self.TTO, True) is None
        self.assert_events( crusher.id
                          , [iid, iid]
                          , [self.TTO, self.TTO]
                          , ['insert identity', 'verify identity']
                           )

    def test_siv_logs_event_when_set_to_false(self):
        crusher = self.make_participant('crusher')
        iid = crusher.store_identity_info(self.TTO, 'nothing-enforced', {'name': 'Crusher'})
        crusher.set_identity_verification(self.TTO, True) is None
        crusher.set_identity_verification(self.TTO, False) is None
        self.assert_events( crusher.id
                          , [iid, iid, iid]
                          , [self.TTO, self.TTO, self.TTO]
                          , ['insert identity', 'verify identity', 'unverify identity']
                           )

    def test_siv_still_logs_an_event_when_noop(self):
        crusher = self.make_participant('crusher')
        crusher.set_identity_verification(self.TTO, True)
        crusher.set_identity_verification(self.TTO, False)
        self.assert_events( crusher.id
                          , [None, None]
                          , [self.TTO, self.TTO]
                          , ['verify identity', 'unverify identity']
                           )


    # ci - clear_identity

    def test_ci_clears_identity(self):
        crusher = self.make_participant('crusher')
        crusher.store_identity_info(self.TTO, 'nothing-enforced', {'name': 'Crusher'})
        assert crusher.clear_identity(self.TTO) is None
        assert crusher.list_identity_metadata() == []

    def test_ci_is_a_noop_when_there_is_no_identity(self):
        crusher = self.make_participant('crusher')
        assert crusher.clear_identity(self.TTO) is None
        assert crusher.list_identity_metadata() == []

    def test_ci_logs_an_event(self):
        crusher = self.make_participant('crusher')
        iid = crusher.store_identity_info(self.TTO, 'nothing-enforced', {'name': 'Crusher'})
        crusher.clear_identity(self.TTO)
        self.assert_events( crusher.id
                          , [iid, iid]
                          , [self.TTO, self.TTO]
                          , ['insert identity', 'clear identity']
                           )

    def test_ci_still_logs_an_event_when_noop(self):
        crusher = self.make_participant('crusher')
        crusher.clear_identity(self.TTO)
        self.assert_events(crusher.id, [None], [self.TTO], ['clear identity'])


    # hvi - has_verified_identity

    def test_hvi_defaults_to_false(self):
        crusher = self.make_participant('crusher')
        assert crusher.has_verified_identity is False

    def test_hvi_is_read_only(self):
        crusher = self.make_participant('crusher')
        with raises(ReadOnly):
            crusher.has_verified_identity = True

    def test_hvi_becomes_true_when_an_identity_is_verified(self):
        crusher = self.make_participant('crusher')
        crusher.store_identity_info(self.TTO, 'nothing-enforced', {})
        crusher.set_identity_verification(self.TTO, True)
        assert Participant.from_username('crusher').has_verified_identity

    def test_hvi_becomes_false_when_the_identity_is_unverified(self):
        crusher = self.make_participant('crusher')
        crusher.store_identity_info(self.TTO, 'nothing-enforced', {})
        crusher.set_identity_verification(self.TTO, True)
        crusher.set_identity_verification(self.TTO, False)
        assert not Participant.from_username('crusher').has_verified_identity

    def test_hvi_stays_true_when_a_secondary_identity_is_verified(self):
        crusher = self.make_participant('crusher')
        crusher.store_identity_info(self.USA, 'nothing-enforced', {})
        crusher.set_identity_verification(self.USA, True)
        crusher.store_identity_info(self.TTO, 'nothing-enforced', {})
        crusher.set_identity_verification(self.TTO, True)
        assert Participant.from_username('crusher').has_verified_identity

    def test_hvi_stays_true_when_the_secondary_identity_is_unverified(self):
        crusher = self.make_participant('crusher')
        crusher.store_identity_info(self.USA, 'nothing-enforced', {})
        crusher.set_identity_verification(self.USA, True)
        crusher.store_identity_info(self.TTO, 'nothing-enforced', {})
        crusher.set_identity_verification(self.TTO, True)
        crusher.set_identity_verification(self.TTO, False)
        assert Participant.from_username('crusher').has_verified_identity

    def test_hvi_goes_back_to_false_when_both_are_unverified(self):
        crusher = self.make_participant('crusher')
        crusher.store_identity_info(self.USA, 'nothing-enforced', {})
        crusher.store_identity_info(self.TTO, 'nothing-enforced', {})
        crusher.set_identity_verification(self.TTO, True)
        crusher.set_identity_verification(self.USA, True)
        crusher.set_identity_verification(self.TTO, False)
        crusher.set_identity_verification(self.USA, False)
        assert not Participant.from_username('crusher').has_verified_identity

    def test_hvi_changes_are_scoped_to_a_participant(self):
        crusher = self.make_participant('crusher')
        crusher.store_identity_info(self.USA, 'nothing-enforced', {})

        bruiser = self.make_participant('bruiser')
        bruiser.store_identity_info(self.USA, 'nothing-enforced', {})

        crusher.set_identity_verification(self.USA, True)

        assert Participant.from_username('crusher').has_verified_identity
        assert not Participant.from_username('bruiser').has_verified_identity

    def test_hvi_resets_when_identity_is_cleared(self):
        crusher = self.make_participant('crusher')
        crusher.store_identity_info(self.TTO, 'nothing-enforced', {})
        crusher.set_identity_verification(self.TTO, True)
        crusher.clear_identity(self.TTO)
        assert not Participant.from_username('crusher').has_verified_identity

    def test_hvi_doesnt_reset_when_penultimate_identity_is_cleared(self):
        crusher = self.make_participant('crusher')
        crusher.store_identity_info(self.USA, 'nothing-enforced', {})
        crusher.set_identity_verification(self.USA, True)
        crusher.store_identity_info(self.TTO, 'nothing-enforced', {})
        crusher.set_identity_verification(self.TTO, True)
        crusher.set_identity_verification(self.TTO, False)
        crusher.clear_identity(self.TTO)
        assert Participant.from_username('crusher').has_verified_identity

    def test_hvi_does_reset_when_both_identities_are_cleared(self):
        crusher = self.make_participant('crusher')
        crusher.store_identity_info(self.USA, 'nothing-enforced', {})
        crusher.store_identity_info(self.TTO, 'nothing-enforced', {})
        crusher.set_identity_verification(self.USA, True)
        crusher.set_identity_verification(self.TTO, True)
        crusher.set_identity_verification(self.TTO, False)
        crusher.set_identity_verification(self.USA, False)
        crusher.clear_identity(self.TTO)
        assert not Participant.from_username('crusher').has_verified_identity
