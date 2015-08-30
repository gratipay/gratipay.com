# encoding: utf8

from __future__ import absolute_import, division, print_function, unicode_literals

from datetime import datetime, timedelta

from aspen import Response, json
from aspen.utils import to_rfc822, utcnow
from dependency_injection import resolve_dependencies
from postgres.cursors import SimpleCursorBase

import gratipay


BEGINNING_OF_EPOCH = to_rfc822(datetime(1970, 1, 1)).encode('ascii')

# Difference between current time and credit card expiring date when
# card is considered as expiring
EXPIRING_DELTA = timedelta(days = 30)


def dict_to_querystring(mapping):
    if not mapping:
        return u''

    arguments = []
    for key, values in mapping.iteritems():
        for val in values:
            arguments.append(u'='.join([key, val]))

    return u'?' + u'&'.join(arguments)


def use_tildes_for_participants(website, request):
    if request.path.raw.startswith('/~/'):
        to = '/~' + request.path.raw[3:]
        if request.qs.raw:
            to += '?' + request.qs.raw
        website.redirect(to)
    elif request.path.raw.startswith('/~'):
        request.path.__init__('/~/' + request.path.raw[2:])


def canonicalize(redirect, path, base, canonical, given, arguments=None):
    if given != canonical:
        assert canonical.lower() == given.lower()  # sanity check
        remainder = path[len(base + given):]

        if arguments is not None:
            arguments = dict_to_querystring(arguments)

        newpath = base + canonical + remainder + arguments or ''
        redirect(newpath)


def get_participant(state, restrict=True, resolve_unclaimed=True):
    """Given a Request, raise Response or return Participant.

    If restrict is True then we'll restrict access to owners and admins.

    """
    redirect = state['website'].redirect
    request = state['request']
    user = state['user']
    slug = request.line.uri.path['username']
    qs = request.line.uri.querystring
    _ = state['_']

    if restrict:
        if user.ANON:
            raise Response(403, _("You need to log in to access this page."))

    from gratipay.models.participant import Participant  # avoid circular import
    participant = Participant.from_username(slug)

    if participant is None:
        raise Response(404)

    canonicalize(redirect, request.line.uri.path.raw, '/~/', participant.username, slug, qs)

    if participant.is_closed:
        if user.ADMIN:
            return participant
        raise Response(410)

    if participant.claimed_time is None and resolve_unclaimed:
        to = participant.resolve_unclaimed()
        if to:
            # This is a stub account (someone on another platform who hasn't
            # actually registered with Gratipay yet)
            redirect(to)
        else:
            # This is an archived account (result of take_over)
            if user.ADMIN:
                return participant
            raise Response(404)

    if restrict:
        if participant != user.participant:
            if not user.ADMIN:
                raise Response(403, _("You are not authorized to access this page."))

    return participant


def get_team(state):
    """Given a Request, raise Response or return Team.
    """
    redirect = state['website'].redirect
    request = state['request']
    user = state['user']
    slug = request.line.uri.path['team']
    qs = request.line.uri.querystring

    from gratipay.models.team import Team  # avoid circular import
    team = Team.from_slug(slug)

    if team is None:
        # Try to redirect to a Participant.
        from gratipay.models.participant import Participant # avoid circular import
        participant = Participant.from_username(slug)
        if participant is not None:
            qs = '?' + request.qs.raw if request.qs.raw else ''
            redirect('/~' + request.path.raw[1:] + qs)
        raise Response(404)

    canonicalize(redirect, request.line.uri.path.raw, '/', team.slug, slug, qs)

    if team.is_closed and not user.ADMIN:
        raise Response(410)

    return team


def update_global_stats(website):
    stats = website.db.one("""
        SELECT nactive, transfer_volume FROM paydays
        ORDER BY ts_end DESC LIMIT 1
    """, default=(0, 0.0))
    website.gnactive = stats[0]
    website.gtransfer_volume = stats[1]

    nreceiving_from = website.db.one("""
        SELECT nreceiving_from
          FROM teams
         WHERE slug = 'Gratipay'
    """, default=0)
    website.support_current = cur = int(round(nreceiving_from / stats[0] * 100)) if stats[0] else 0
    if cur < 10:    goal = 20
    elif cur < 15:  goal = 30
    elif cur < 25:  goal = 40
    elif cur < 35:  goal = 50
    elif cur < 45:  goal = 60
    elif cur < 55:  goal = 70
    elif cur < 65:  goal = 80
    elif cur > 70:  goal = None
    website.support_goal = goal


def _execute(this, sql, params=[]):
    print(sql.strip(), params)
    super(SimpleCursorBase, this).execute(sql, params)

def log_cursor(f):
    "Prints sql and params to stdout. Works globaly so watch for threaded use."
    def wrapper(*a, **kw):
        try:
            SimpleCursorBase.execute = _execute
            ret = f(*a, **kw)
        finally:
            del SimpleCursorBase.execute
        return ret
    return wrapper


def format_money(money):
    format = '%.2f' if money < 1000 else '%.0f'
    return format % money


def excerpt_intro(text, length=175, append=u'…'):
    if not text:
        return ''
    if len(text) > length:
        return text[:length] + append
    return text


def is_card_expiring(expiration_year, expiration_month):
    now = datetime.utcnow()
    expiring_date = datetime(expiration_year, expiration_month, 1)
    delta = expiring_date - now
    return delta < EXPIRING_DELTA


def set_cookie(cookies, key, value, expires=None, httponly=True, path=b'/'):
    cookies[key] = value
    cookie = cookies[key]
    if expires:
        if isinstance(expires, timedelta):
            expires += utcnow()
        if isinstance(expires, datetime):
            expires = to_rfc822(expires).encode('ascii')
        cookie[b'expires'] = expires
    if httponly:
        cookie[b'httponly'] = True
    if path:
        cookie[b'path'] = path
    if gratipay.use_secure_cookies:
        cookie[b'secure'] = True


def erase_cookie(cookies, key, **kw):
    set_cookie(cookies, key, '', BEGINNING_OF_EPOCH, **kw)


def filter_profile_nav(user, participant, pages):
    out = []
    for foo, bar, show_them, show_others in pages:
        if (user.participant == participant and show_them) \
        or (user.participant != participant and show_others) \
        or user.ADMIN:
            out.append((foo, bar, show_them, show_others))
    return out


def to_javascript(obj):
    """For when you want to inject an object into a <script> tag.
    """
    return json.dumps(obj).replace('</', '<\\/')


class LazyResponse(Response):

    def __init__(self, code, lazy_body, **kw):
        Response.__init__(self, code, '', **kw)
        self.lazy_body = lazy_body

    def render_body(self, state):
        f = self.lazy_body
        self.body = f(*resolve_dependencies(f, state).as_args)
