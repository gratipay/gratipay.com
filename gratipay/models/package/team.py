# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import uuid

from gratipay.models.team import Team as _Team


class Team(object):
    """A :py:class:`~gratipay.models.package.Package` can have a
    :py:class:`~gratipay.models.team.Team` associated with it.
    """

    @property
    def team(self):
        """A computed attribute, the :py:class:`~gratipay.models.team.Team`
        linked to this package if there is one, otherwise ``None``. Makes a
        database call.
        """
        return self.load_team(self.db)


    def load_team(self, cursor):
        """Given a database cursor, return a
        :py:class:`~gratipay.models.team.Team` if there is one linked to this
        package, or ``None`` if not.
        """
        return cursor.one( 'SELECT t.*::teams FROM teams t WHERE t.id='
                           '(SELECT team_id FROM teams_to_packages tp WHERE tp.package_id=%s)'
                         , (self.id,)
                          )


    def get_or_create_linked_team(self, cursor, owner):
        """Given a db cursor and a :py:class:`Participant`, return a
        :py:class:`~gratipay.models.team.Team`.
        """
        team = self.load_team(cursor)
        if team:
            return team

        def slug_options():
            # Having analyzed existing names, we should never get `@` without
            # `/`. Be conservative in what we accept! Oh, wait ...
            base_name = self.name.split('/')[1] if self.name.startswith('@') else self.name
            yield base_name
            for i in range(1, 10):
                yield '{}-{}'.format(base_name, i)
            yield uuid.uuid4().hex

        for slug in slug_options():
            if cursor.one('SELECT count(*) FROM teams WHERE slug=%s', (slug,)) == 0:
                break

        team = _Team.insert( slug=slug
                           , slug_lower=slug.lower()
                           , name=slug
                           , homepage='https://www.npmjs.com/package/' + self.name
                           , product_or_service=self.description
                           , owner=owner
                           , _cursor=cursor
                            )
        cursor.run('INSERT INTO teams_to_packages (team_id, package_id) '
                   'VALUES (%s, %s)', (team.id, self.id))
        self.app.add_event( cursor
                          , 'package'
                          , dict(id=self.id, action='link', values=dict(team_id=team.id))
                           )
        return team


    def unlink_team(self, cursor):
        """Given a db cursor, unlink the team associated with this package
        (it's a bug if called with no team linked).
        """
        team = self.load_team(cursor)
        assert team is not None  # sanity check
        cursor.run('DELETE FROM teams_to_packages WHERE package_id=%s', (self.id,))
        self.app.add_event( cursor
                          , 'package'
                          , dict(id=self.id, action='unlink', values=dict(team_id=team.id))
                           )
