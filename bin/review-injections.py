#!/usr/bin/env python
from __future__ import absolute_import, division, print_function, unicode_literals

import os
import re

high_risk = []
low_risk = []

for root, dirs, files in os.walk('www'):
    for filename in files:
        if not filename.endswith('.spt'):
            continue
        filepath = os.path.join(root, filename)
        if os.path.islink(filepath):
            continue
        curblock = ['', -1, -1]
        for i, line in enumerate(open(filepath), start=1):
            line = line.decode('utf8')
            if '{{' in line:
                curblock[1] = i
            if curblock[1] == -1:
                continue
            curblock[0] += " " + line.strip()
            if '}}' in line:
                curblock[2] = i

            if curblock[2] > -1:
                replacements = re.search(r'({{.+?}})', curblock[0])
                if replacements:
                    for replacement in replacements.groups():
                        if curblock[1] != curblock[2]:
                            linerange = "{}-{}".format(*curblock[1:])
                        else:
                            linerange = "{}".format(curblock[1])

                        if re.match(r'^{{ _\("[A-Za-z0-9 ,.!]+?"\) }}$', replacement):
                            queue = low_risk
                        else:
                            queue = high_risk

                        queue.append((filepath, linerange, replacement))
                curblock = ['', -1, -1]

for name, queue in (("High Risk", high_risk), ("Low Risk", low_risk)):
    header = "{} (N={})".format(name, len(queue))
    print(header)
    print("="*len(header))
    for filepath, linerange, replacement in queue:
        print("{}  {:>9}  {}".format(filepath, linerange, replacement))
    print()
