from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing import Harness
from gratipay.models.team import mixins


class Tests(Harness):

    def test_team_object_subclasses_payroll_mixin(self):
        enterprise = self.make_team('The Enterprise')
        assert isinstance(enterprise, mixins.Payroll)


    # atp - add_to_payroll

    def test_atp_adds_to_payroll(self):
        enterprise = self.make_team('The Enterprise')
        crusher = self.make_participant('crusher')
        enterprise.add_to_payroll(crusher)
        assert crusher in enterprise


    # rfp - remove_from_payroll

    def test_rfp_removes_from_payroll(self):
        enterprise = self.make_team('The Enterprise')
        crusher = self.make_participant('crusher')
        enterprise.add_to_payroll(crusher)
        enterprise.remove_from_payroll(crusher)
        assert crusher not in enterprise
