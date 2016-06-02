from __future__ import absolute_import, division, print_function, unicode_literals

from decimal import Decimal as D
from gratipay.testing import Harness
from gratipay.models.participant import Participant
from gratipay.models.team import Team


P = Participant.from_username
T = Team.from_slug


class Tests(Harness):

    def setUp(self):
        self.alice = self.make_participant('alice', claimed_time='now', last_bill_result='')
        self.bob = self.make_participant('bob', claimed_time='now', last_bill_result='')
        self.enterprise = self.make_team()


    # g - giving

    def test_g_starts_out_zero(self):
        assert P('alice').giving == 0

    def test_g_increases_with_payment_instruction(self):
        self.alice.set_payment_instruction(self.enterprise, '1.00')
        assert P('alice').giving == D('1.00')


    # ngt - ngiving_to

    def test_ngt_starts_out_zero(self):
        assert P('alice').ngiving_to == 0

    def test_ngt_increases_with_payment_instruction(self):
        self.alice.set_payment_instruction(self.enterprise, '1.00')
        assert P('alice').ngiving_to == 1


    # r - receiving

    def test_r_starts_out_zero(self):
        assert T('TheEnterprise').receiving == 0

    def test_r_increases_with_payment_instruction(self):
        self.alice.set_payment_instruction(self.enterprise, '1.00')
        assert T('TheEnterprise').receiving == D('1.00')


    # nrf - nreceiving_from

    def test_nrf_starts_out_zero(self):
        assert T('TheEnterprise').nreceiving_from == 0

    def test_nrf_increases_with_payment_instruction(self):
        self.alice.set_payment_instruction(self.enterprise, '1.00')
        assert T('TheEnterprise').nreceiving_from == 1
