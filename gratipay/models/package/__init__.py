# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from postgres.orm import Model


NPM = 'npm'  # We are starting with a single package manager. If we see
             # traction we will expand.


class Package(Model):
    """Represent a gratipackage. :-)
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


    # Emails
    # ======

    def send_confirmation_email(self, address):
        pass
