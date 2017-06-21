# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals


class FakeProject(object):

    def __init__(self, website, package):
        self.website = website
        self.package = package
        self.name = package.name
        self.url_path = '/on/{}/{}/'.format(package.package_manager, package.name)

    def get_image_url(self, size):
        assert size in ('large', 'small'), size
        return self.website.asset('package-default-{}.png'.format(size))


def with_unclaimed_packages_wrapped(website, projects_and_unclaimed_packages):
    out = []
    for project, unclaimed_package in projects_and_unclaimed_packages:
        if unclaimed_package:
            assert project is None
            project = FakeProject(website, unclaimed_package)
        out.append(project)
    return out
