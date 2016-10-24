from __future__ import absolute_import, division, print_function, unicode_literals

import json
from cStringIO import StringIO

import mock

from gratipay import chomp
from gratipay.testing import Harness
from gratipay.models.package import Package


A11Y_ANNOUNCER = json.loads('{"a11y-announcer":{"name":"a11y-announcer","description":"An accessible ember route change announcer","dist-tags":{"latest":"1.0.2"},"maintainers":[{"name":"alice","email":"alice@example.com"}],"homepage":"https://github.com/ember-a11y/a11y-announcer#readme","keywords":["ember-addon","ember accessibility","ember router","a11y-announcer"],"repository":{"type":"git","url":"git+https://github.com/ember-a11y/a11y-announcer.git"},"author":{"name":"Alice Hacker"},"bugs":{"url":"https://github.com/ember-a11y/a11y-announcer/issues"},"license":"MIT","readmeFilename":"README.md","users":{"jalcine":true,"unwiredbrain":true},"time":{"modified":"2016-08-13T23:03:37.135Z"},"versions":{"1.0.2":"latest"}}}')


class Tests(Harness):

    # rcf - read_catalog_for

    @mock.patch('gratipay.chomp.NPM.fetch_catalog')
    def test_rcf_reads_catalog_for(self, fetch_catalog):
        fetch_catalog.return_value = A11Y_ANNOUNCER
        with self.db.get_cursor() as cursor:
            pm = chomp.NPM()
            package_manager_id = chomp.insert_package_manager(pm, cursor)
            setattr(pm, 'id', package_manager_id)
            packages, emails = chomp.read_catalog_for(pm, cursor)
        assert packages.read() == '\t'.join([ '1'
                                            , str(package_manager_id)
                                            , 'a11y-announcer'
                                            , 'An accessible ember route change announcer'
                                            , '2016-08-13T23:03:37.135Z'
                                             ]) + '\n'
        assert emails.read() == '\t'.join([ '1', 'alice@example.com']) + '\n'


    # cid - copy_into_db

    @mock.patch('gratipay.chomp.NPM.fetch_catalog')
    def test_cid_copies_to_database(self, fetch_catalog):
        with self.db.get_cursor() as cursor:
            pm = chomp.NPM()
            package_manager_id = chomp.insert_package_manager(pm, cursor)
            packages = StringIO('\t'.join([ '0'
                                          , str(package_manager_id)
                                          , 'foobar'
                                          , 'Foos barringly'
                                          , '2016-08-13T23:03:37.135Z'
                                           ]))
            emails = StringIO('\t'.join(['0', 'alice@example.com']))
            chomp.copy_into_db(cursor, packages, emails)
        p = Package.from_names('npm', 'foobar')
        assert p.name == 'foobar'
