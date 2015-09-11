from __future__ import absolute_import, division, print_function, unicode_literals

from aspen import renderers


class Renderer(renderers.Renderer):
    def render_content(self, context):
        return eval(self.compiled, globals(), context)

class Factory(renderers.Factory):
    Renderer = Renderer
