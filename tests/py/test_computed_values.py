from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing import Harness
from gratipay.models.exchange_route import ExchangeRoute
from gratipay.models.participant import Participant
from gratipay.models.team import Team


P = Participant.from_username
T = Team.from_slug


class Tests(Harness):

    def setUp(self):
        self.alice = self.make_participant('alice', claimed_time='now', last_bill_result='')
        self.bob = self.make_participant('bob', claimed_time='now', last_bill_result='')
        self.enterprise = self.make_team()

        self.carl = self.make_participant('carl', claimed_time='now')
        self.carl.set_payment_instruction(self.enterprise, 10)


    # if - is_funded

    def test_if_starts_out_false_when_no_route(self):
        assert not self.carl.get_payment_instruction(self.enterprise)['is_funded']

    def test_if_becomes_true_when_working_route_added(self):
        route = ExchangeRoute.insert(self.carl, 'braintree-cc', '/cards/foo', '')
        assert self.carl.get_payment_instruction(self.enterprise)['is_funded']
        return route

    def test_if_becomes_false_when_route_stops_working(self):
        route = self.test_if_becomes_true_when_working_route_added()
        route.update_error('cheese')
        assert not self.carl.get_payment_instruction(self.enterprise)['is_funded']

    def test_if_stays_false_when_nonworking_route_added(self):
        route = ExchangeRoute.insert(self.carl, 'braintree-cc', '/cards/foo', 'cheese')
        assert not self.carl.get_payment_instruction(self.enterprise)['is_funded']
        return route

    def test_if_becomes_true_when_route_starts_working(self):
        route = self.test_if_stays_false_when_nonworking_route_added()
        route.update_error('')
        assert self.carl.get_payment_instruction(self.enterprise)['is_funded']

    def test_if_is_unaffected_by_payout_route(self):
        payout_route = ExchangeRoute.insert(self.carl, 'paypal', 'foo@example.com', '')
        assert not self.carl.get_payment_instruction(self.enterprise)['is_funded']
        payout_route.update_error('cheese')
        assert not self.carl.get_payment_instruction(self.enterprise)['is_funded']
