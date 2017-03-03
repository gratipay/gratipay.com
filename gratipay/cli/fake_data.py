# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay import fake_data, wireup
from gratipay.models import check_db


def _wireup():
    env = wireup.env()
    db = wireup.db(env)
    wireup.crypto(env)
    return db


def main(db=None, *a, **kw):
    db = db or _wireup()
    fake_data.clean_db(db)
    fake_data.prep_db(db)
    fake_data.populate_db(db, *a, **kw)
    fake_data.clean_db(db)
    check_db(db)
