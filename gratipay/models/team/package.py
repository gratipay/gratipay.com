# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals


class Package(object):
    """A :py:class:`~gratipay.models.team.Team` can have a
    :py:class:`~gratipay.models.package.Package` associated with it.
    Linking/unlinking API is over on ``Package``.
    """

    @property
    def package(self):
        """A computed attribute, the
        :py:class:`~gratipay.models.package.Package` linked to this team if
        there is one, otherwise ``None``. Makes a database call.
        """
        return self.load_package(self.db)


    def load_package(self, cursor):
        """Given a database cursor, return a
        :py:class:`~gratipay.models.package.Package` if there is one linked to
        this team, or ``None`` if not.
        """
        return cursor.one( 'SELECT p.*::packages FROM packages p WHERE p.id='
                           '(SELECT package_id FROM teams_to_packages tp WHERE tp.team_id=%s)'
                         , (self.id,)
                          )
