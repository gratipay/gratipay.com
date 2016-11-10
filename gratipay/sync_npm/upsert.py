# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import uuid


NULL = uuid.uuid4().hex  # coordinate with Postgres on how to say "NULL"


def main(env, args, db):
    """Take a CSV file from stdin and load it into Postgres.
    """
    fp = open(args.path)
    with db.get_cursor() as cursor:
        assert cursor.connection.encoding == 'UTF8'

        # http://tapoueh.org/blog/2013/03/15-batch-update.html
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
