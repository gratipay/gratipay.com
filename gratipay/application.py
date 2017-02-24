# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from . import utils, wireup
from .cron import Cron
from .models.participant import Participant
from .version import get_version

from .website import Website


class Application(object):
    """Represent the Gratipay application, a monolith.
    """

    def __init__(self):
        website = Website(self)

        website.configure_renderers()
        # *Now* do wireup. It depends on renderers to ... compile assets or
        # some such?
        env, db, tell_sentry = self.wireup(website)
        website.modify_algorithm(tell_sentry)
        website.monkey_patch_response()

        self.install_periodic_jobs(website, env, db)

        self.website = website


    def wireup(self, website):
        exc = None
        try:
            website.version = get_version()
        except Exception, e:
            exc = e
            website.version = 'x'

        env = wireup.env()
        db = wireup.db(env)
        tell_sentry = wireup.make_sentry_teller(env)

        # TODO Move these directly onto self.
        website.env = env
        website.db = db
        website.tell_sentry = tell_sentry

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

        if exc:
            tell_sentry(exc, {})

        return env, db, tell_sentry


    def install_periodic_jobs(self, website, env, db):
        cron = Cron(website)
        cron(env.update_cta_every, lambda: utils.update_cta(website))
        cron(env.check_db_every, db.self_check, True)
        cron(env.dequeue_emails_every, Participant.dequeue_emails, True)
