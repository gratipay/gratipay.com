"""Navigation aides for Building Gittip.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import OrderedDict
from os.path import join, realpath, isfile, isdir

from aspen import resources
from aspen.http.request import Request
from aspen.resources.static_resource import StaticResource


def get_simplate_context(website, fs):
    request = Request()
    request.fs = fs
    request.website = website
    resource = resources.get(request)
    return {} if isinstance(resource, StaticResource) else resource.pages[0]


class NavItem(OrderedDict):

    by_fs = {}  # intentionally class-global
    by_url = {}

    def __init__(self, website, parent, fs, slug):
        OrderedDict.__init__(self)
        self.parent = parent
        self.fs = fs
        self.url = '/' if parent is None else \
                   '/'.join([parent.url if parent.url != '/' else '', slug])

        self.by_fs[fs] = self
        self.by_url[self.url] = self

        self.slug = slug

        if isdir(fs):
            simplate = self.find_index(website.indices, fs)
        elif fs.endswith('.spt'):
            simplate = fs
        else:
            simplate = None

        context = {}
        if simplate is not None:
            context = get_simplate_context(website, simplate)
            slugs = context.get('nav_children', [])
            for slug in slugs:
                new_fs = join(fs, slug)
                if not isdir(new_fs):
                    new_fs += '.spt'
                child = NavItem(website, self, new_fs, slug)
                self[child.slug] = child  # Populate self as an OrderedDict

        self.title = context.get('nav_title', '[Untitled]')


    def __str__(self):
        return '<NavItem: {}>'.format(self.url)
    __repr__ = __str__


    @property
    def children(self):
        return self.values()


    def find_index(self, indices, fs):
        for name in indices:
            candidate = realpath(join(fs, name))
            if isfile(candidate):
                return candidate
        return fs
