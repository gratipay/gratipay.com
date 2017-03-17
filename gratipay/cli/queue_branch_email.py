# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import sys
import random

from gratipay.application import Application


def get_recently_active_participants(db):
    return db.all("""
        SELECT p.*::participants
          FROM participants p
         WHERE email_address is not null
           AND claimed_time  is not null
           AND is_closed     is not true
           AND is_suspicious is not true
           AND ( SELECT count(*)
                   FROM exchanges e
                  WHERE e.participant = p.username
                    AND timestamp > now() - '180 days'::interval
                ) > 0
      ORDER BY p.username ASC
    """)


def main(_argv=sys.argv, _input=raw_input, _print=print, _app=None):
    """This is a script to enqueue global site notification emails.

    It should only be used for important transactional messages like a Terms of
    Service change. Process:

        - write your email in emails/branch.spt
        - test locally using your own database and AWS keys in local.env
        - when reviewed and merged:
            - deploy
            - `heroku run bash`
            - `queue-branch-email your_username`      # final test from production
            - `queue-branch-email all 2> queued.log`  # !!!
            - make a commit to master to empty branch.spt
              (leave an empty file [but with speclines] or tests will fail)
            - push to GitHub

    """
    app = _app or Application()

    def prompt(msg):
        answer = _input(msg + " [y/N]")
        if answer.lower() != 'y':
            raise SystemExit(1)


    # Fetch participants.
    # ===================

    try:
        username = _argv[1]
    except IndexError:
        _print("Usage: {0} [username|all]".format(_argv[0]))
        raise SystemExit

    if username == 'all':
        prompt("Are you ready?")
        prompt("Are you REALLY ready?")
        prompt("... ?")
        _print("Okay, you asked for it!")
        participants = get_recently_active_participants(app.db)
    else:
        _print("Okay, just {}.".format(username))
        participants = app.db.all("SELECT p.*::participants FROM participants p "
                                  "WHERE p.username=%s", (username,))

    N = len(participants)
    _print(N)
    for p in random.sample(participants, 5 if N > 5 else 1) if N else []:
        _print("spotcheck: {} ({}={})".format(p.email_address, p.username, p.id))


    # Send emails.
    # ============

    if username == 'all':
        prompt("But really actually tho? I mean, ... seriously?")

    for i, p in enumerate(participants, start=1):
        _print( "{:>4} queuing for {} ({}={})".format(i, p.email_address, p.username, p.id)
              , file=sys.stderr
               )
        app.email_queue.put(p, 'branch', include_unsubscribe=False, _user_initiated=False)
