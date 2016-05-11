from __future__ import absolute_import, division, print_function, unicode_literals

from postgres.orm import Model


class Country(Model):
    """Represent country records from our database (read-only).

    :var int id: the record's primary key in our ``countries`` table
    :var unicode name: the name of the country
    :var unicode code2: the country's `ISO 3166-1 alpha-2`_ code
    :var unicode code3: the country's `ISO 3166-1 alpha-3`_ code

    .. _ISO 3166-1 alpha-2 : https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2
    .. _ISO 3166-1 alpha-3 : https://en.wikipedia.org/wiki/ISO_3166-1_alpha-3

    """
    typname = 'countries'
