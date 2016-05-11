from __future__ import absolute_import, division, print_function, unicode_literals

from postgres.orm import Model


class Country(Model):
    """Represent country records from our database (read-only).

    :var int id: the record's primary key in our ``countries`` table
    :var unicode code: the country's `ISO 3166-1 alpha-2`_ code

    .. _ISO 3166-1 alpha-2 : https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2

    """
    typname = 'countries'
