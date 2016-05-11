from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing import Harness


class TeamTakesHarness(Harness):
    # Factored out to share with membership tests ...

    def setUp(self):
        self.enterprise = self.make_team('The Enterprise')

        self.TT = self.db.one("SELECT id FROM countries WHERE code2='TT'")

        self.crusher = self.make_participant( 'crusher'
                                            , email_address='crusher@example.com'
                                            , claimed_time='now'
                                             )
        self.crusher.store_identity_info(self.TT, 'nothing-enforced', {'name': 'Crusher'})
        self.crusher.set_identity_verification(self.TT, True)

        self.bruiser = self.make_participant( 'bruiser'
                                            , email_address='bruiser@example.com'
                                            , claimed_time='now'
                                             )
        self.bruiser.store_identity_info(self.TT, 'nothing-enforced', {'name': 'Bruiser'})
        self.bruiser.set_identity_verification(self.TT, True)


class Tests(TeamTakesHarness):

    # sn - set_ntakes

    def test_sn_sets_ntakes(self):
        assert self.enterprise.set_ntakes(1024) == 1024

    def test_sn_actually_sets_ntakes(self):
        self.enterprise.set_ntakes(1024)
        assert self.db.one("SELECT ntakes FROM teams") == self.enterprise.ntakes == 1024

    def test_sn_wont_set_ntakes_below_zero(self):
        assert self.enterprise.set_ntakes(-1) == 0

    def test_sn_wont_set_ntakes_below_nclaimed(self):
        self.enterprise.set_ntakes(1024)
        self.enterprise.set_ntakes_for(self.crusher, 128)
        assert self.enterprise.set_ntakes(-1024) == 128

    def test_sn_affects_cacheroonies_as_expected(self):
        assert self.enterprise.ntakes == 0
        assert self.enterprise.ntakes_claimed == 0
        assert self.enterprise.ntakes_unclaimed == 0

        self.enterprise.set_ntakes(1024)
        assert self.enterprise.ntakes == 1024
        assert self.enterprise.ntakes_claimed == 0
        assert self.enterprise.ntakes_unclaimed == 1024

        self.enterprise.set_ntakes_for(self.crusher, 128)

        self.enterprise.set_ntakes(-1024)
        assert self.enterprise.ntakes == 128
        assert self.enterprise.ntakes_claimed == 128
        assert self.enterprise.ntakes_unclaimed == 0


    # snf - set_ntakes_for

    def test_snf_sets_ntakes_for(self):
        self.enterprise.set_ntakes(1000)
        assert self.enterprise.set_ntakes_for(self.crusher, 537) == 537

    def test_snf_actually_sets_ntakes_for(self):
        self.enterprise.set_ntakes(1000)
        self.enterprise.set_ntakes_for(self.crusher, 537)
        assert self.db.one("SELECT ntakes FROM takes") == 537

    def test_snf_takes_as_much_as_is_available(self):
        self.enterprise.set_ntakes(1000)
        assert self.enterprise.set_ntakes_for(self.crusher, 1000) == 1000

    def test_snf_caps_ntakes_to_the_number_available(self):
        self.enterprise.set_ntakes(1000)
        assert self.enterprise.set_ntakes_for(self.crusher, 1024) == 1000

    def test_snf_works_with_another_member_present(self):
        self.enterprise.set_ntakes(1000)
        assert self.enterprise.set_ntakes_for(self.bruiser, 537) == 537
        assert self.enterprise.set_ntakes_for(self.crusher, 537) == 463

    def test_snf_affects_cacheroonies_as_expected(self):
        self.enterprise.set_ntakes(1000)
        self.enterprise.set_ntakes_for(self.bruiser, 537)
        self.enterprise.set_ntakes_for(self.crusher, 128)
        assert self.enterprise.nmembers == 2
        assert self.enterprise.ntakes_claimed == 665
        assert self.enterprise.ntakes_unclaimed == 335

    def test_snf_sets_ntakes_properly_for_an_existing_member(self):
        self.enterprise.set_ntakes(1000)
        assert self.enterprise.set_ntakes_for(self.crusher, 537) == 537
        assert self.enterprise.set_ntakes_for(self.bruiser, 537) == 463
        assert self.enterprise.set_ntakes_for(self.crusher, 128) == 128
        assert self.enterprise.nmembers == 2
        assert self.enterprise.ntakes_claimed   ==  463 + 128 == 591
        assert self.enterprise.ntakes_unclaimed == 1000 - 591 == 409
