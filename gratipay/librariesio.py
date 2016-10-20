from __future__ import absolute_import, division, print_function, unicode_literals

import re
import requests
import json


def extract_package_names(full):
    lines = full.splitlines()
    start = 0
    end = -1
    for i, line in enumerate(lines):
        if not start and line.startswith('<ul class="top-level">'):
            start = i
        elif line.startswith('<ins class="adsbygoogle"'):
            end = i
    part = '\n'.join(lines[start:end-1])
    return sorted(set(re.findall(r'<a href="[^"]*">(.*)</a>', part)))


def resolve(package_json):
    """Takes a package.json file contents, returns JSON.
    """
    package_json = json.loads(package_json)

    r = requests.get(url='http://libraries.io/npm/{name}/tree'.format(**package_json))
    if r.status_code == 200:
        # The package.json has a package name that also exists on npm. Assume this is that.
        names = extract_package_names(r.text)
        names.remove(package_json['name'])

    return names
