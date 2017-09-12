# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import psycopg2.extras

from . import email, sync_npm, utils
from .cron import Cron
from .models import GratipayDB
from .card_charger import CardCharger
from .payday_runner import PaydayRunner
from .project_review_process import ProjectReviewProcess
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
        db = self.db = GratipayDB(self, url=env.database_url, maxconn=env.database_maxconn)
        tell_sentry = self.tell_sentry = wireup.make_sentry_teller(env)

        website.init_more(env, db, tell_sentry) # TODO Fold this into Website.__init__

        wireup.crypto(env)
        wireup.base_url(website, env)
        wireup.secure_cookies(env)
        wireup.billing(env)
        wireup.username_restrictions(website)
        wireup.load_i18n(website.project_root, tell_sentry)
        wireup.other_stuff(website, env)
        wireup.accounts_elsewhere(website, env)

        website.init_even_more()                # TODO Fold this into Website.__init__
        self.email_queue = email.Queue(env, db, tell_sentry, website.project_root)
        self.install_periodic_jobs(website, env, db)
        self.website = website
        self.payday_runner = PaydayRunner(self)
        self.project_review_process = ProjectReviewProcess(env, db, self.email_queue)
        self.pfos_card_charger = CardCharger(online=env.load_braintree_form_on_homepage)


    def install_periodic_jobs(self, website, env, db):
        cron = Cron(website)
        cron(env.update_cta_every, website.update_cta)
        cron(env.check_db_every, db.self_check, True)
        cron(env.check_npm_sync_every, lambda: sync_npm.check(db))
        cron(env.email_queue_flush_every, self.email_queue.flush, True)
        cron(env.email_queue_log_metrics_every, self.email_queue.log_metrics)


    def add_event(self, c, type, payload):
        """Log an event.

        This is the function we use to capture interesting events that happen
        across the system in one place, the ``events`` table.

        :param c: a :py:class:`Postgres` or :py:class:`Cursor` instance
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
