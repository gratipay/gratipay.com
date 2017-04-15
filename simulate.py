#!/usr/bin/env python
"""This script simulates an HTTP request and spits out a profiling report.

Invoke it like so:

    $ foreman run -e local.env ./simulate.py /

"""
from __future__ import absolute_import, division, print_function, unicode_literals

import cProfile
import os
import sys

from aspen.website import Website


def main(path, run_through_profiler):

    # There's some chdir happening (in aspen.testing.fsfix, maybe?) that is
    # landing is in www/ already by the time we get here. Let's work from the
    # location of this script to set the proper paths.

    project_root = os.path.realpath(os.path.dirname(__file__))
    www_root = os.path.join(project_root, 'www')
    import pdb; pdb.set_trace()
    website = Website(['--www_root', www_root, '--project_root', project_root])

    # The next line does a chdir as a side-effect. Eep! :^(
    from gittip.testing.client import TestClient

    client = TestClient(website=website)
    if run_through_profiler:
        profiler = cProfile.Profile()
        profiler.runcall(client.get, path)
        profiler.print_stats(sort=2)
    else:
        print(client.get(path).body)


if __name__ == '__main__':

    if '-x' in sys.argv:
        run_through_profiler = False
        sys.argv.remove('-x')
    else:
        run_through_profiler = True

    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        path = '/'

    main(path, run_through_profiler)
