from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing import Harness
from gratipay.models.team import mixins


class Tests(Harness):

    def test_team_object_subclasses_payroll_mixin(self):
        enterprise = self.make_team('The Enterprise')
        assert isinstance(enterprise, mixins.Payroll)
