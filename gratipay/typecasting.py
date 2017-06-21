# -*- coding: utf-8 -*-
"""Fork of aspen.typecasting to clean some stuff up. Upstream it, ya?
"""
from __future__ import absolute_import, division, print_function, unicode_literals

from dependency_injection import resolve_dependencies


def cast(website, request, state):
    """Implement typecasting (differently from stock Aspen).

    When matching paths, Aspen looks for ``/%foo/`` and then foo is a variable
    with the value in the URL path, so ``/bar/`` would end up with
    ``foo='bar'``.

    There's a dictionary at ``website.typecasters`` that maps variable names to
    functions, dependency-injectable as with ``website.algorithm``
    (state-chain) functions. If an entry exists in ``typecasters`` for a given
    path variable, then the value of ``path[part]`` is replaced with the result
    of calling the function.

    Before calling your cast function, we add an additional value to the state
    dict at ``path_part``: the URL path part that matched, as a string. That is
    user input, so handle it carefully. It's your job to raise
    ``Response(40x)`` if it's bad input.

    """
    typecasters = website.typecasters
    path = request.line.uri.path

    for part in path.keys():
        if part not in typecasters:
            continue
        state['path_part'] = path[part]
        path.popall(part)
        func = typecasters[part]
        path[part] = func(*resolve_dependencies(func, state).as_args)
