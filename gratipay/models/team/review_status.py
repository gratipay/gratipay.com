# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals


class ReviewStatus(object):
    """This is a mixin to provide review status API on the Team object. Teams
    must be approved before they can use Gratipay to receive and distribute
    funds.
    """

    @property
    def status(self):
        """The review status of the team.
        """
        return { None: 'unreviewed'
               , False: 'rejected'
               , True: 'approved'
                }[self.is_approved]


    def update_review_status(self, status, recorder):
        """Takes the new status as a string and a participant object for the
        admin making the change.
        """
        with self.db.get_cursor() as cursor:
            is_approved = {'approved': True, 'rejected': False, 'unreviewed': None}[status]
            if not(is_approved is self.is_approved):
                self._set_is_approved(cursor, is_approved, recorder)


    def _set_is_approved(self, cursor, is_approved, recorder):
        is_approved = self.db.one("""

            UPDATE teams
               SET is_approved=%s
             WHERE slug=%s
         RETURNING is_approved

            """, (is_approved, self.slug))

        self.set_attributes(is_approved=is_approved)

        status = {True: 'approved', False: 'rejected', None: 'unreviewed'}[is_approved]

        self.app.add_event(cursor, 'team', dict(
            id=self.id,
            recorder=dict(id=recorder.id, username=recorder.username),
            action='set', values=dict(status=status)
        ))

        if status in ('rejected', 'approved'):
            from ..participant import Participant
            owner = Participant.from_username(self.owner)
            self.app.email_queue.put( owner
                                    , 'team-'+status
                                    , team_name=self.name
                                    , review_url=self.review_url
                                    , include_unsubscribe=False
                                    , _user_initiated=False
                                     )
