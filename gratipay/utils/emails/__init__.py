from __future__ import absolute_import, division, print_function, unicode_literals

import sys

from aspen.simplates.pagination import parse_specline, split_and_escape
from aspen_jinja2_renderer import SimplateLoader
from jinja2 import Environment


( VERIFICATION_MISSING
, VERIFICATION_FAILED
, VERIFICATION_EXPIRED
, VERIFICATION_REDUNDANT
, VERIFICATION_STYMIED
, VERIFICATION_SUCCEEDED
 ) = range(6)


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
