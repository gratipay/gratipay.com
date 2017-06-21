# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import traceback

from gratipay.testing.browser import NeverLeft


def test_fail_repr():
    try:
        raise NeverLeft('.some.selector')
    except:
        formatted = traceback.format_exc()
        assert 'NeverLeft: .some.selector' in formatted
