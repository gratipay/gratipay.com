from __future__ import absolute_import, division, print_function, unicode_literals


class PayrollMixin(object):
    """This mixing provides management of payroll for
    :py:class:`~gratipay.models.team.Team` objects.
    """


    def add_to_payroll(self, participant):
        """Add a participant to the team's payroll.
        """
        raise NotImplementedError


    def remove_from_payroll(self, participant):
        """Remove a participant from the team's payroll.
        """
        raise NotImplementedError
