# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import os
import pickle
import sys
from time import sleep

import boto3
from aspen import log_dammit
from aspen.simplates.pagination import parse_specline, split_and_escape
from aspen_jinja2_renderer import SimplateLoader
from jinja2 import Environment
from markupsafe import escape as htmlescape

from gratipay.exceptions import Throttled
from gratipay.models.participant import Participant
from gratipay.utils import find_files, i18n


class Queue(object):
    """Model an outbound email queue.
    """

    def __init__(self, env, db, tell_sentry, root):
        if self._have_ses(env):
            log_dammit("AWS SES is configured! We'll send mail through SES.")
            self._mailer = boto3.client( service_name='ses'
                                       , region_name=env.aws_ses_default_region
                                       , aws_access_key_id=env.aws_ses_access_key_id
                                       , aws_secret_access_key=env.aws_ses_secret_access_key
                                        )
        else:
            log_dammit("AWS SES is not configured! Mail will be dumped to the console here.")
            self._mailer = ConsoleMailer()

        self.db = db
        self.tell_sentry = tell_sentry
        self.sleep_for = env.email_queue_sleep_for
        self.allow_up_to = env.email_queue_allow_up_to

        templates = {}
        templates_dir = os.path.join(root, 'emails')
        assert os.path.isdir(templates_dir)
        i = len(templates_dir) + 1
        for spt in find_files(templates_dir, '*.spt'):
            base_name = spt[i:-4]
            templates[base_name] = compile_email_spt(spt)
        self._email_templates = templates


    def _have_ses(self, env):
        return env.aws_ses_access_key_id \
           and env.aws_ses_secret_access_key \
           and env.aws_ses_default_region


    def put(self, to, template, _user_initiated=True, email=None, **context):
        """Put an email message on the queue.

        :param Participant to: the participant to send the email message to.
            In cases where an email is not linked to a participant, this can be
            ``None``.
        :param unicode template: the name of the template to use when rendering
            the email, corresponding to a filename in ``emails/`` without the
            file extension
        :param unicode email: The email address to send this message to. If not
            provided, the ``to`` participant's primary email is used.
        :param bool _user_initiated: user-initiated emails are throttled;
            system-initiated messages don't count against throttling
        :param dict context: the values to use when rendering the template

        :raise Throttled: if the participant already has a few messages in the
            queue (that they put there); the specific number is tunable with
            the ``EMAIL_QUEUE_ALLOW_UP_TO`` envvar.

        :returns: ``None``

        """

        assert to or email # Either participant or email address required.

        with self.db.get_cursor() as cursor:
            participant_id = to.id if to else None
            cursor.run("""
                INSERT INTO email_queue
                            (participant,
                             email_address,
                             spt_name,
                             context,
                             user_initiated)
                     VALUES (%s, %s, %s, %s, %s)
            """, (participant_id, email, template, pickle.dumps(context), _user_initiated))

            if _user_initiated:
                nqueued = self._get_nqueued(cursor, to, email)
                if nqueued > self.allow_up_to:
                    raise Throttled()


    def _get_nqueued(self, cursor, participant, email_address):
        """Returns the number of messages already queued for the given
        participant or email address. Prefers participant if provided, falls
        back to email_address otherwise.

        :param Participant participant: The participant to check queued messages
            for.

        :param unicode email_address: The email address to check queued messages
            for.

        :returns number of queued messages
        """

        if participant:
            return cursor.one("""
                SELECT COUNT(*)
                  FROM email_queue
                 WHERE user_initiated
                   AND participant=%s
            """, (participant.id, ))
        else:
            return cursor.one("""
                SELECT COUNT(*)
                  FROM email_queue
                 WHERE user_initiated
                   AND email_address=%s
            """, (email_address, ))


    def flush(self):
        """Load messages queued for sending, and send them.
        """
        fetch_messages = lambda: self.db.all("""
            SELECT *
              FROM email_queue
             WHERE not dead
          ORDER BY id ASC
             LIMIT 60
        """)
        nsent = 0
        while True:
            messages = fetch_messages()
            if not messages:
                break
            for rec in messages:
                try:
                    r = self._flush_one(rec)
                except:
                    self.db.run("UPDATE email_queue SET dead=true WHERE id = %s", (rec.id,))
                    raise
                self.db.run("DELETE FROM email_queue WHERE id = %s", (rec.id,))
                if r == 1:
                    sleep(self.sleep_for)
                nsent += r
        return nsent


    def _flush_one(self, rec):
        """Send an email message using the underlying ``_mailer``.

        :param Record rec: a database record from the ``email_queue`` table
        :return int: the number of emails sent (0 or 1)

        """
        message = self._prepare_email_message_for_ses(rec)
        if message is None:
            return 0 # Not sent
        self._mailer.send_email(**message)
        return 1 # Sent


    def _prepare_email_message_for_ses(self, rec):
        """Prepare an email message for delivery via Amazon SES.

        :param Record rec: a database record from the ``email_queue`` table

        :returns: ``None`` if we can't find an email address to send to
        :returns: ``dict`` if we can find an email address to send to

        We look for an email address to send to in two places:

        #. the context stored in ``rec.context``, and then
        #. ``participant.email_address``.

        """
        participant = Participant.from_id(rec.participant)
        spt = self._email_templates[rec.spt_name]
        context = pickle.loads(rec.context)

        email = rec.email_address or participant.email_address

        # Previously, email_address was stored in the 'email' key on `context`
        # and not in the `email_address` field. Let's handle that case so that
        # old emails don't suffer
        #
        # TODO: Remove this once we're sure old emails have gone out.
        email = context.get('email', email)

        if not email:
            return None

        context['email'] = email
        if participant:
            context['participant'] = participant
            context['username'] = participant.username
        context['button_style'] = (
            "color: #fff; text-decoration:none; display:inline-block; "
            "padding: 0 15px; background: #396; white-space: nowrap; "
            "font: normal 14px/40px Arial, sans-serif; border-radius: 3px"
        )
        context.setdefault('include_unsubscribe', True)

        accept_lang = (participant and participant.email_lang) or 'en'
        langs = i18n.parse_accept_lang(accept_lang)
        locale = i18n.match_lang(langs)
        i18n.add_helpers_to_context(self.tell_sentry, context, locale)
        context['escape'] = lambda s: s
        context_html = dict(context)
        i18n.add_helpers_to_context(self.tell_sentry, context_html, locale)
        context_html['escape'] = htmlescape
        base_spt = self._email_templates['base']
        def render(t, context):
            b = base_spt[t].render(context).strip()
            return b.replace('$body', spt[t].render(context).strip())

        message = {}
        message['Source'] = 'Gratipay Support <support@gratipay.com>'
        message['Destination'] = {}
        if participant:
            # "username <email@domain.com>"
            destination = "%s <%s>" % (participant.username, email)
        else:
            destination = email
        message['Destination']['ToAddresses'] = [destination]
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
        return message


    def log_metrics(self, _print=print):
        ndead = self.db.one('SELECT COUNT(*) FROM email_queue WHERE dead')
        ntotal = self.db.one('SELECT COUNT(*) FROM email_queue')
        _print('count#email_queue_dead=%d count#email_queue_total=%d' % (ndead, ntotal))


    def purge(self):
        """Remove all messages from the queue.
        """
        self.db.run('DELETE FROM email_queue')


jinja_env = Environment()
jinja_env_html = Environment(autoescape=True, extensions=['jinja2.ext.autoescape'])

def compile_email_spt(fpath):
    """Compile an email template from a simplate.

    :param unicode fpath: the filesystem path of the simplate

    """
    r = {}
    with open(fpath) as f:
        pages = list(split_and_escape(f.read()))
    for i, page in enumerate(pages, 1):
        tmpl = b'\n' * page.offset + page.content
        content_type, renderer = parse_specline(page.header)
        key = 'subject' if i == 1 else content_type
        env = jinja_env_html if content_type == 'text/html' else jinja_env
        r[key] = SimplateLoader(fpath, tmpl).load(env, fpath)
    return r


class ConsoleMailer(object):
    """Dumps mail to stdout.
    """

    def __init__(self, fp=sys.stdout):
        self.fp = fp

    def send_email(self, **email):
        p = lambda *a, **kw: print(*a, file=self.fp)
        p('-'*78, )
        for i, address in enumerate(email['Destination']['ToAddresses']):
            if not i:
                p('To:      ', address)
            else:
                p('         ', address)
        p('Subject: ', email['Message']['Subject']['Data'])
        p('Body:')
        p()
        for line in email['Message']['Body']['Text']['Data'].splitlines():
            p('   ', line)
        p()
        p('-'*78)
