from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.models import add_event


class TakesMixin(object):
    """This mixin provides management of takes for
    :py:class:`~gratipay.models.team.Team` objects.
    """

    def set_takes_enabled(self, to):
        """Update whether takes are enabled for this team.

        :param bool to: whether the team should have takes enabled

        """
        if type(to) is not bool:
            raise TypeError('Boolean required.')
        with self.db.get_cursor() as cursor:
            cursor.run("UPDATE teams SET takes_enabled=%s WHERE id=%s", (to, self.id))
            add_event( cursor
                     , 'team'
                     , dict( action='set takes_enabled'
                           , id=self.id
                           , old_value=self.takes_enabled
                           , new_value=to
                            )
                      )
