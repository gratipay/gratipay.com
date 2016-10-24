from __future__ import absolute_import, division, print_function, unicode_literals

from postgres import orm


class Package(orm.Model):
    typname = 'packages';

    @classmethod
    def from_names(cls, package_manager_name, package_name):
        return cls.db.one("""

        SELECT p.*::packages
          FROM packages p
          JOIN package_managers pm ON p.package_manager_id = pm.id
         WHERE pm.name=%s AND p.name=%s

        """, (package_manager_name, package_name))
