from __future__ import absolute_import, division, print_function, unicode_literals

from postgres import orm


class Package(orm.Model):
    typname = 'packages';

    @classmethod
    def from_names(cls, package_manager, name):
        return cls.db.one("""

        SELECT p.*::packages
          FROM packages p
         WHERE p.package_manager=%s AND p.name=%s

        """, (package_manager, name))
