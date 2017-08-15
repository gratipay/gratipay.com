# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import OrderedDict


PRIMARY, VERIFIED, UNVERIFIED, UNLINKED, OTHER = \
                                               'primary verified unverified unlinked other'.split()


class Emails(object):
    """A :py:class:`~gratipay.models.package.Package` has emails associated
    with it, which we use to verify package ownership.
    """

    def classify_emails_for_participant(self, participant):
        """List email addresses on file for this package, classified by their
        relevance to the participant in question. Returns a list of
        ``(address, classification)`` string tuples, sorted by
        classification as follows:

          - primary
          - verified
          - unverified
          - unlinked
          - other

        Emails are alphabetical within each classification.

        """
        package_emails_by_group = OrderedDict(( (PRIMARY, [])
                                              , (VERIFIED, [])
                                              , (UNVERIFIED, [])
                                              , (UNLINKED, [])
                                              , (OTHER, [])
                                               ))

        group_by_participant_email = {}
        for email in participant.get_emails():
            if email.address == participant.email_address:
                group = PRIMARY
            elif email.verified:
                group = VERIFIED
            else:
                group = UNVERIFIED
            group_by_participant_email[email.address] = group

        other_verified = self.db.all('''

            SELECT address
              FROM email_addresses
             WHERE verified is true
               AND participant_id != %s
               AND address = ANY((SELECT emails FROM packages WHERE id=%s)::text[])
          ORDER BY address ASC

        ''', (participant.id, self.id))

        for email in sorted(self.emails):
            group = group_by_participant_email.get(email)
            if not group:
                group = OTHER if email in other_verified else UNLINKED
            package_emails_by_group[group].append(email)

        out = []
        for group in package_emails_by_group:
            for email in package_emails_by_group[group]:
                out.append((email, group))
        return out
