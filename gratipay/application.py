# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import psycopg2.extras

from . import utils
from .cron import Cron
from .models import GratipayDB
from .models.participant import Participant
from .payday_runner import PaydayRunner
from .website import Website


class Application(object):
    """Represent the Gratipay application, a monolith.
    """

    def __init__(self):

        # Eventually we want to move all of the wireup functionality into
        # objects as we've done with Website, GratipayDB, email.Queue, and
        # PaydayRunner. For now, dodge a circular import.

        from . import wireup

        utils.i18n.set_locale()
        website = Website(self)

        env = self.env = wireup.env()
        db = self.db = GratipayDB(self, env.database_url, env.database_maxconn)
        tell_sentry = self.tell_sentry = wireup.make_sentry_teller(env)

        website.init_more(env, db, tell_sentry) # TODO Fold this into Website.__init__

        wireup.crypto(env)
        wireup.mail(env, website.project_root)
        wireup.base_url(website, env)
        wireup.secure_cookies(env)
        wireup.billing(env)
        wireup.team_review(env)
        wireup.username_restrictions(website)
        wireup.load_i18n(website.project_root, tell_sentry)
        wireup.other_stuff(website, env)
        wireup.accounts_elsewhere(website, env)

        website.init_even_more()                # TODO Fold this into Website.__init__
        self.install_periodic_jobs(website, env, db)
        self.website = website
        self.payday_runner = PaydayRunner(self)


    def install_periodic_jobs(self, website, env, db):
        cron = Cron(website)
        cron(env.update_cta_every, lambda: utils.update_cta(website))
        cron(env.check_db_every, db.self_check, True)
        cron(env.dequeue_emails_every, Participant.dequeue_emails, True)


    def add_event(self, c, type, payload):
        """Log an event.

        This is the function we use to capture interesting events that happen
        across the system in one place, the ``events`` table.

        :param c: a :py:class:`Postres` or :py:class:`Cursor` instance
        :param unicode type: an indicator of what type of event it is--either ``participant``,
          ``team`` or ``payday``
        :param payload: an arbitrary JSON-serializable data structure; for ``participant`` type,
          ``id`` must be the id of the participant in question

        """
        SQL = """
            INSERT INTO events (type, payload)
            VALUES (%s, %s)
        """
        c.run(SQL, (type, psycopg2.extras.Json(payload)))
