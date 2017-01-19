# -*- coding: utf-8 -*-
"""Subcommand for upserting data from a CSV into Postgres.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import uuid

from . import sentry


# Coordinate with Postgres on how to say "NULL".
# ==============================================
# We can't use the default, which is the empty string, because then we can't
# easily store the empty string itself. We don't want to use something that a
# package author could maliciously or mischieviously take advantage of to
# indicate a null we don't want. If we use a uuid it should be hard enough to
# guess, made harder in that it will change for each processing run.

NULL = uuid.uuid4().hex


def upsert(env, args, db):
    fp = open(args.path)
    with db.get_cursor() as cursor:
        assert cursor.connection.encoding == 'UTF8'

        cursor.run("CREATE TEMP TABLE updates (LIKE packages INCLUDING ALL) ON COMMIT DROP")
        cursor.copy_expert('COPY updates (package_manager, name, description, emails) '
                           "FROM STDIN WITH (FORMAT csv, NULL '%s')" % NULL, fp)
        cursor.run("""

            WITH updated AS (
                UPDATE packages p
                   SET package_manager = u.package_manager
                     , description = u.description
                     , emails = u.emails
                  FROM updates u
                 WHERE p.name = u.name
             RETURNING p.name
            )
            INSERT INTO packages(package_manager, name, description, emails)
                 SELECT package_manager, name, description, emails
                   FROM updates u LEFT JOIN updated USING(name)
                  WHERE updated.name IS NULL
               GROUP BY u.package_manager, u.name, u.description, u.emails

        """)


def main(env, args, db):
    """Take a CSV file from stdin and load it into Postgres using an `ingenious algorithm`_.

    .. _ingenious algorithm:  http://tapoueh.org/blog/2013/03/15-batch-update.html

    """
    with sentry(env):
        upsert(env, args, db)
