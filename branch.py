#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import sys

from gratipay.utils import markdown
from gratipay import wireup


db = wireup.db(wireup.env())

statements = db.all('SELECT s.*, username FROM statements s '
                    'JOIN participants p ON s.participant=p.id '
                    'ORDER BY participant, lang ASC')

for i, statement in enumerate(statements):
    try:
        scrubbed = markdown.render_and_scrub(statement.content)
    except Exception as exc:
        print(exc.__class__.__name__, statement.participant, statement.username, file=sys.stderr)
        continue
    db.run( 'UPDATE statements SET content_scrubbed=%s WHERE participant=%s AND lang=%s'
          , (scrubbed, statement.participant, statement.lang)
           )
    print('\r{:>5}'.format(i), end='')

print()
