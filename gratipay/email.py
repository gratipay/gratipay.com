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


    def put(self, to, template, **context):
        """Put an email message on the queue.

        :param Participant to: the participant to send the email message to
        :param unicode template: the name of the template to use when rendering
          the email, corresponding to a filename in ``emails/`` without the file
          extension
        :param dict context: the values to use when rendering the template

        """
        self.db.run("""
            INSERT INTO email_queue
                        (participant, spt_name, context)
                 VALUES (%s, %s, %s)
        """, (to.id, template, pickle.dumps(context)))


    def flush(self):
        """Load messages queued for sending, and send them.
        """
        fetch_messages = lambda: self.db.all("""
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
                p = Participant.from_id(msg.participant)
                r = self._flush_one(p, msg.spt_name, **pickle.loads(msg.context))
                self.db.run("DELETE FROM email_queue WHERE id = %s", (msg.id,))
                if r == 1:
                    sleep(1)
                nsent += r
        return nsent


    def _flush_one(self, to, template, **context):
        context['participant'] = to
        context['username'] = to.username
        context['button_style'] = (
            "color: #fff; text-decoration:none; display:inline-block; "
            "padding: 0 15px; background: #396; white-space: nowrap; "
            "font: normal 14px/40px Arial, sans-serif; border-radius: 3px"
        )
        context.setdefault('include_unsubscribe', True)
        email = context.setdefault('email', to.email_address)
        if not email:
            return 0 # Not Sent
        langs = i18n.parse_accept_lang(to.email_lang or 'en')
        locale = i18n.match_lang(langs)
        i18n.add_helpers_to_context(self.tell_sentry, context, locale)
        context['escape'] = lambda s: s
        context_html = dict(context)
        i18n.add_helpers_to_context(self.tell_sentry, context_html, locale)
        context_html['escape'] = htmlescape
        spt = self._email_templates[template]
        base_spt = self._email_templates['base']
        def render(t, context):
            b = base_spt[t].render(context).strip()
            return b.replace('$body', spt[t].render(context).strip())

        message = {}
        message['Source'] = 'Gratipay Support <support@gratipay.com>'
        message['Destination'] = {}
        message['Destination']['ToAddresses'] = ["%s <%s>" % (to.username, email)] # "Name <email@domain.com>"
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


jinja_env = Environment()
jinja_env_html = Environment(autoescape=True, extensions=['jinja2.ext.autoescape'])

def compile_email_spt(fpath):
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
