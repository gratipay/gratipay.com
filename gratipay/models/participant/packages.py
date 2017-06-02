# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.exceptions import NoPackages


class Packages(object):

    def start_package_claims(self, c, nonce, *packages):
        """Takes a cursor, nonce and list of packages, inserts into ``claims``
        and returns ``None`` (or raise :py:exc:`NoPackages`).
        """
        if not packages:
            raise NoPackages()

        # We want to make a single db call to insert all claims, so we need to
        # do a little SQL construction. Do it in such a way that we still avoid
        # Python string interpolation (~= SQLi vector).

        extra_sql, values = [], []
        for p in packages:
            extra_sql.append('(%s, %s)')
            values += [nonce, p.id]
        c.run('INSERT INTO claims (nonce, package_id) VALUES' + ', '.join(extra_sql), values)
        self.app.add_event( c
                          , 'participant'
                          , dict( id=self.id
                                , action='start-claim'
                                , values=dict(package_ids=[p.id for p in packages])
                                 )
                               )


    def get_packages_claiming(self, cursor, nonce):
        """Given a nonce, return :py:class:`~gratipay.models.package.Package`
        objects associated with it.
        """
        return cursor.all("""
            SELECT p.*::packages
              FROM packages p
              JOIN claims c
                ON p.id = c.package_id
             WHERE c.nonce=%s
          ORDER BY p.name ASC
        """, (nonce,))


    def finish_package_claims(self, cursor, nonce, *packages):
        """Create teams if needed and associate them with the packages.
        """
        if not packages:
            raise NoPackages()

        package_ids, teams, team_ids = [], [], []
        for package in packages:
            package_ids.append(package.id)
            team = package.get_or_create_linked_team(cursor, self)
            teams.append(team)
            team_ids.append(team.id)
        review_url = self.app.project_review_repo.create_issue(*teams)

        cursor.run('DELETE FROM claims WHERE nonce=%s', (nonce,))
        cursor.run('UPDATE teams SET review_url=%s WHERE id=ANY(%s)', (review_url, team_ids,))
        self.app.add_event( cursor
                          , 'participant'
                          , dict( id=self.id
                                , action='finish-claim'
                                , values=dict(package_ids=package_ids)
                                 )
                               )
