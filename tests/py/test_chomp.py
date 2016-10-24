from __future__ import absolute_import, division, print_function, unicode_literals

import json

import mock

from gratipay import chomp
from gratipay.testing import Harness
from gratipay.models.package import Package


A11Y_ANNOUNCER = json.loads('{"a11y-announcer":{"name":"a11y-announcer","description":"An accessible ember route change announcer","dist-tags":{"latest":"1.0.2"},"maintainers":[{"name":"robdel12","email":"Robertdeluca19@gmail.com"}],"homepage":"https://github.com/ember-a11y/a11y-announcer#readme","keywords":["ember-addon","ember accessibility","ember router","a11y-announcer"],"repository":{"type":"git","url":"git+https://github.com/ember-a11y/a11y-announcer.git"},"author":{"name":"Robert DeLuca"},"bugs":{"url":"https://github.com/ember-a11y/a11y-announcer/issues"},"license":"MIT","readmeFilename":"README.md","users":{"jalcine":true,"unwiredbrain":true},"time":{"modified":"2016-08-13T23:03:37.135Z"},"versions":{"1.0.2":"latest"}}}')


class Tests(Harness):

    # icf - insert_catalog_for

    @mock.patch('gratipay.chomp.NPM.fetch_catalog')
    def test_icf_inserts_catalog_for(self, fetch_catalog):
        fetch_catalog.return_value = A11Y_ANNOUNCER
        with self.db.get_cursor() as cursor:
            pm = chomp.NPM()
            package_manager_id = chomp.insert_package_manager(pm, cursor)
            setattr(pm, 'id', package_manager_id)
            chomp.insert_catalog_for(pm, cursor)
        p = Package.from_names('npm', 'a11y-announcer')
        assert p.name == 'a11y-announcer'
