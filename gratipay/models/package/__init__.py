# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from postgres.orm import Model

from .emails import Emails
from .team import Team


NPM = 'npm'  # We are starting with a single package manager. If we see
             # traction we will expand.


class Package(Model, Emails, Team):
    """Represent a gratipackage. :-)

    Packages are entities on open source package managers; `npm
    <https://www.npmjs.com/>`_ is the only one we support so far. Each package
    on npm has a page on Gratipay with an URL of the form ``/on/npm/foo/``.
    Packages can be claimed by Gratipay participants, at which point we create
    a :py:class:`~gratipay.models.team.Team` for them under the hood so they
    can start accepting payments.

    """

    typname = 'packages'

    def __eq__(self, other):
        if not isinstance(other, Package):
            return False
        return self.id == other.id

    def __ne__(self, other):
        if not isinstance(other, Package):
            return True
        return self.id != other.id


    @property
    def url_path(self):
        """The path part of the URL for this package on Gratipay.
        """
        return '/on/{}/{}/'.format(self.package_manager, self.name)


    @property
    def remote_human_url(self):
        """The URL for the main page for this package on its package manager.
        """
        if self.package_manager == NPM:
            return 'https://www.npmjs.com/package/{}'.format(self.name)
        raise NotImplementedError()


    @property
    def remote_api_url(self):
        """The main API URL for this package on its package manager.
        """
        if self.package_manager == NPM:
            return 'https://registry.npmjs.com/{}'.format(self.name)
        raise NotImplementedError()


    # Constructors
    # ============

    @classmethod
    def from_id(cls, id):
        """Return an existing package based on id.
        """
        return cls.db.one("SELECT packages.*::packages FROM packages WHERE id=%s", (id,))

    @classmethod
    def from_names(cls, package_manager, name):
        """Return an existing package based on package manager and package names.
        """
        return cls.db.one("SELECT packages.*::packages FROM packages "
                          "WHERE package_manager=%s and name=%s", (package_manager, name))
