from __future__ import absolute_import, division, print_function, unicode_literals

from subprocess import Popen, PIPE

import json
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


def render_like_npm(markdown, package=None):
    """Process markdown the same way npm does.

    Package should be a dict representing the package. If it includes `name`
    and `description` then the first h1 and paragraph will have a
    'package-{name,description}-redundant' class added to them if they're
    similar enough. If it includes `repository.url` then links will be changed
    somehow. For details consult the docs and code:

    https://github.com/npm/marky-markdown

    """
    if type(markdown) is unicode:
        markdown = markdown.encode('utf8')
    cmd = ("bin/our-marky-markdown.js", "/dev/stdin")
    if package:
        cmd += (json.dumps(package),)
    marky = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    out, err = marky.communicate(markdown)
    if marky.wait() > 0:
        raise OSError(err)
    return out

