# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import OrderedDict


def make(htmlfunc, var, current, *names):
    """Helper to spit out a struct for rendering tabs (see templates/nav-tabs.html).
    """
    tabs = OrderedDict()
    tabs[names[0]] = {}
    for name in names[1:]:
        tabs[name] = {var: name}
    for name, tab in tabs.iteritems():
        tab['link'] = '?{}={}'.format(var, tab[var]) if var in tab else '.'
        tab['is_selected'] = (tab.get(var) == current)
        tab['html'] = htmlfunc(name, tab)
    return list(tabs.values())
