from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing import Harness
from psycopg2 import IntegrityError
from pytest import raises


class Tests(Harness):

    def test_available_defaults_to_zero(self):
        assert self.make_team().available == 0

    def test_available_cant_be_negative(self):
        self.make_team()
        raises(IntegrityError, self.db.run, "UPDATE teams SET available = -537")

    def test_available_can_be_positive(self):
        self.make_team()
        self.db.run("UPDATE teams SET available = 537")
        assert self.db.one("SELECT available FROM teams") == 537

    def test_available_works_in_the_test_factory(self):
        assert self.make_team(available=537).available == 537
