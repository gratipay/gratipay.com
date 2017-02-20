# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import pickle
import uuid
from datetime import timedelta
from time import sleep

from aspen.utils import utcnow
from markupsafe import escape as htmlescape
from psycopg2 import IntegrityError

import gratipay
from gratipay.exceptions import EmailAlreadyTaken, CannotRemovePrimaryEmail, EmailNotVerified
from gratipay.exceptions import TooManyEmailAddresses, ResendingTooFast
from gratipay.models import add_event
from gratipay.security.crypto import constant_time_compare
from gratipay.utils import emails, encode_for_querystring, i18n


EMAIL_HASH_TIMEOUT = timedelta(hours=24)


class Email(object):

    def add_email(self, email, resend_threshold='3 minutes'):
        """
            This is called when
            1) Adding a new email address
            2) Resending the verification email for an unverified email address

            Returns the number of emails sent.
        """

        # Check that this address isn't already verified
        owner = self.db.one("""
            SELECT p.username
              FROM emails e INNER JOIN participants p
                ON e.participant_id = p.id
             WHERE e.address = %(email)s
               AND e.verified IS true
        """, locals())
        if owner:
            if owner == self.username:
                return 0
            else:
                raise EmailAlreadyTaken(email)

        if len(self.get_emails()) > 9:
            raise TooManyEmailAddresses(email)

        nonce = str(uuid.uuid4())
        verification_start = utcnow()

        nrecent = self.db.one( "SELECT count(*) FROM emails WHERE address=%s AND "
                               "%s - verification_start < %s"
                             , (email, verification_start, resend_threshold)
                              )
        if nrecent:
            raise ResendingTooFast()

        try:
            with self.db.get_cursor() as c:
                add_event(c, 'participant', dict(id=self.id, action='add', values=dict(email=email)))
                c.run("""
                    INSERT INTO emails
                                (address, nonce, verification_start, participant_id)
                         VALUES (%s, %s, %s, %s)
                """, (email, nonce, verification_start, self.id))
        except IntegrityError:
            nonce = self.db.one("""
                UPDATE emails
                   SET verification_start=%s
                 WHERE participant_id=%s
                   AND address=%s
                   AND verified IS NULL
             RETURNING nonce
            """, (verification_start, self.id, email))
            if not nonce:
                return self.add_email(email)

        base_url = gratipay.base_url
        username = self.username_lower
        encoded_email = encode_for_querystring(email)
        link = "{base_url}/~{username}/emails/verify.html?email2={encoded_email}&nonce={nonce}"
        r = self.send_email('verification',
                            email=email,
                            link=link.format(**locals()),
                            include_unsubscribe=False)
        assert r == 1 # Make sure the verification email was sent
        if self.email_address:
            self.send_email('verification_notice',
                            new_email=email,
                            include_unsubscribe=False)
            return 2
        return 1

    def update_email(self, email):
        if not getattr(self.get_email(email), 'verified', False):
            raise EmailNotVerified(email)
        username = self.username
        with self.db.get_cursor() as c:
            add_event(c, 'participant', dict(id=self.id, action='set', values=dict(primary_email=email)))
            c.run("""
                UPDATE participants
                   SET email_address=%(email)s
                 WHERE username=%(username)s
            """, locals())
        self.set_attributes(email_address=email)

    def verify_email(self, email, nonce):
        if '' in (email, nonce):
            return emails.VERIFICATION_MISSING
        r = self.get_email(email)
        if r is None:
            return emails.VERIFICATION_FAILED
        if r.verified:
            assert r.nonce is None  # and therefore, order of conditions matters
            return emails.VERIFICATION_REDUNDANT
        if not constant_time_compare(r.nonce, nonce):
            return emails.VERIFICATION_FAILED
        if (utcnow() - r.verification_start) > EMAIL_HASH_TIMEOUT:
            return emails.VERIFICATION_EXPIRED
        try:
            self.db.run("""
                UPDATE emails
                   SET verified=true, verification_end=now(), nonce=NULL
                 WHERE participant_id=%s
                   AND address=%s
                   AND verified IS NULL
            """, (self.id, email))
        except IntegrityError:
            return emails.VERIFICATION_STYMIED

        if not self.email_address:
            self.update_email(email)
        return emails.VERIFICATION_SUCCEEDED

    def get_email(self, email):
        return self.db.one("""
            SELECT *
              FROM emails
             WHERE participant_id=%s
               AND address=%s
        """, (self.id, email))

    def get_emails(self):
        return self.db.all("""
            SELECT *
              FROM emails
             WHERE participant_id=%s
          ORDER BY id
        """, (self.id,))

    def get_verified_email_addresses(self):
        return [email.address for email in self.get_emails() if email.verified]

    def remove_email(self, address):
        if address == self.email_address:
            raise CannotRemovePrimaryEmail()
        with self.db.get_cursor() as c:
            add_event(c, 'participant', dict(id=self.id, action='remove', values=dict(email=address)))
            c.run("DELETE FROM emails WHERE participant_id=%s AND address=%s",
                  (self.id, address))

    def send_email(self, spt_name, **context):
        context['participant'] = self
        context['username'] = self.username
        context['button_style'] = (
            "color: #fff; text-decoration:none; display:inline-block; "
            "padding: 0 15px; background: #396; white-space: nowrap; "
            "font: normal 14px/40px Arial, sans-serif; border-radius: 3px"
        )
        context.setdefault('include_unsubscribe', True)
        email = context.setdefault('email', self.email_address)
        if not email:
            return 0 # Not Sent
        langs = i18n.parse_accept_lang(self.email_lang or 'en')
        locale = i18n.match_lang(langs)
        i18n.add_helpers_to_context(self._tell_sentry, context, locale)
        context['escape'] = lambda s: s
        context_html = dict(context)
        i18n.add_helpers_to_context(self._tell_sentry, context_html, locale)
        context_html['escape'] = htmlescape
        spt = self._emails[spt_name]
        base_spt = self._emails['base']
        def render(t, context):
            b = base_spt[t].render(context).strip()
            return b.replace('$body', spt[t].render(context).strip())

        message = {}
        message['Source'] = 'Gratipay Support <support@gratipay.com>'
        message['Destination'] = {}
        message['Destination']['ToAddresses'] = ["%s <%s>" % (self.username, email)] # "Name <email@domain.com>"
        message['Message'] = {}
        message['Message']['Subject'] = {}
        message['Message']['Subject']['Data'] = spt['subject'].render(context).strip()
        message['Message']['Body'] = {
            'Text': {
                'Data': render('text/plain', context)
            },
            'Html': {
                'Data': render('text/html', context_html)
            }
        }

        self._mailer.send_email(**message)
        return 1 # Sent

    def queue_email(self, spt_name, **context):
        self.db.run("""
            INSERT INTO email_queue
                        (participant, spt_name, context)
                 VALUES (%s, %s, %s)
        """, (self.id, spt_name, pickle.dumps(context)))

    @classmethod
    def dequeue_emails(cls):
        fetch_messages = lambda: cls.db.all("""
            SELECT *
              FROM email_queue
          ORDER BY id ASC
             LIMIT 60
        """)
        nsent = 0
        while True:
            messages = fetch_messages()
            if not messages:
                break
            for msg in messages:
                p = cls.from_id(msg.participant)
                r = p.send_email(msg.spt_name, **pickle.loads(msg.context))
                cls.db.run("DELETE FROM email_queue WHERE id = %s", (msg.id,))
                if r == 1:
                    sleep(1)
                nsent += r
        return nsent

    def set_email_lang(self, accept_lang):
        if not accept_lang:
            return
        self.db.run("UPDATE participants SET email_lang=%s WHERE id=%s",
                    (accept_lang, self.id))
        self.set_attributes(email_lang=accept_lang)
