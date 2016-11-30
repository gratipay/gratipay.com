from __future__ import absolute_import, division, print_function, unicode_literals


import misaka as m  # http://misaka.61924.nl/
from markupsafe import Markup


def render(markdown):
    """Process markdown approximately the same way that GitHub used to.

    (Note that as of November, 2016 they are migrating to CommonMark, so we are
    starting to drift.)

    """
    return Markup(m.html(
        markdown,
        extensions=m.EXT_AUTOLINK | m.EXT_STRIKETHROUGH | m.EXT_NO_INTRA_EMPHASIS,
        render_flags=m.HTML_SKIP_HTML | m.HTML_TOC | m.HTML_SMARTYPANTS | m.HTML_SAFELINK
    ))
