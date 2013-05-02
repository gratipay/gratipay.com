from aspen import Response
from aspen.utils import typecheck
from tornado.escape import linkify
from gittip.models.participant import Participant
import pycountry

COUNTRIES = [(country.alpha3, country.name) for country in pycountry.countries]
COUNTRIES_MAP = dict(COUNTRIES)


def wrap(u):
    """Given a unicode, return a unicode.
    """
    typecheck(u, unicode)
    u = linkify(u)  # Do this first, because it calls xthml_escape.
    u = u.replace(u'\r\n', u'<br />\r\n').replace(u'\n', u'<br />\n')
    return u if u else '...'


def canonicalize(path, base, canonical, given):
    if given != canonical:
        assert canonical.lower() == given.lower()  # sanity check
        remainder = path[len(base + given):]
        newpath = base + canonical + remainder
        raise Response(302, headers={"Location": newpath})


def get_participant(request, restrict=True):
    """Given a Request, raise Response or return Participant.

    If user is not None then we'll restrict access to owners and admins.

    """
    user = request.context['user']
    slug = request.line.uri.path['username']

    if restrict:
        if user.ANON:
            request.redirect(u'/%s/' % slug)

    participant = \
           Participant.query.filter_by(username_lower=slug.lower()).first()

    if participant is None:
        raise Response(404)

    canonicalize(request.line.uri.path.raw, '/', participant.username, slug)

    if participant.claimed_time is None:

        # This is a stub participant record for someone on another platform who
        # hasn't actually registered with Gittip yet. Let's bounce the viewer
        # over to the appropriate platform page.

        to = participant.resolve_unclaimed()
        if to is None:
            raise Response(404)
        request.redirect(to)

    if restrict:
        if participant != user:
            if not user.ADMIN:
                raise Response(403)

    return participant
