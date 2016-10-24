from __future__ import absolute_import, division, print_function, unicode_literals

from postgres import orm


class Package(orm.Model):
    typname = 'packages';

    @classmethod
    def from_platform_and_name(cls, platform, name):
        return cls.db.one("SELECT packages.*::packages from packages where "
                          "platform=%s and name=%s;", (platform, name,))
