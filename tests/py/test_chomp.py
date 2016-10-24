from __future__ import absolute_import, division, print_function, unicode_literals

import json
from io import StringIO

from gratipay import chomp
from gratipay.testing import Harness
from gratipay.models.package import Package


CATALOG = json.loads('{"a11y-announcer":{"name":"a11y-announcer","description":"An accessible ember route change announcer","dist-tags":{"latest":"1.0.2"},"maintainers":[{"name":"alice","email":"alice@example.com"}],"homepage":"https://github.com/ember-a11y/a11y-announcer#readme","keywords":["ember-addon","ember accessibility","ember router","a11y-announcer"],"repository":{"type":"git","url":"git+https://github.com/ember-a11y/a11y-announcer.git"},"author":{"name":"Alice Hacker"},"bugs":{"url":"https://github.com/ember-a11y/a11y-announcer/issues"},"license":"MIT","readmeFilename":"README.md","users":{"jalcine":true,"unwiredbrain":true},"time":{"modified":"2016-08-13T23:03:37.135Z"},"versions":{"1.0.2":"latest"}}}')


class Tests(Harness):

    # eifc - extract_info_from_catalog

    def test_eifc_extracts_info_from_catalog(self):
        pm = chomp.NPM()
        packages, emails = chomp.extract_info_from_catalog(pm, CATALOG)
        assert packages.read() == '\t'.join([ '1'
                                            , 'npm'
                                            , 'a11y-announcer'
                                            , 'An accessible ember route change announcer'
                                            , '2016-08-13T23:03:37.135Z'
                                             ]) + '\n'
        assert emails.read() == '\t'.join([ '1', 'alice@example.com']) + '\n'


    # cid - copy_into_db

    def test_cid_copies_into_database(self):
        with self.db.get_cursor() as cursor:
            packages = StringIO('\t'.join([ '0'
                                          , 'npm'
                                          , 'foobar'
                                          , 'Foos barringly'
                                          , '2016-08-13T23:03:37.135Z'
                                           ]))
            emails = StringIO('\t'.join(['0', 'alice@example.com']))
            chomp.copy_into_db(cursor, packages, emails)
        p = Package.from_names('npm', 'foobar')
        assert p.name == 'foobar'
