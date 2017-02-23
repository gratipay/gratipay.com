# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals


class Closing(object):
    """This mixin implements team closing.
    """

    #: Whether the team is closed or not.

    is_closed = False


    def close(self):
        """Close the team account.
        """
        with self.db.get_cursor() as cursor:
            cursor.run("UPDATE teams SET is_closed=true WHERE id=%s", (self.id,))
            self.app.add_event( cursor
                              , 'team'
                              , dict(id=self.id, action='set', values=dict(is_closed=True))
                               )
            self.set_attributes(is_closed=True)
