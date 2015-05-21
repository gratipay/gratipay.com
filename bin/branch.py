#!/usr/bin/env python
from __future__ import print_function

import csv
import sys


DETAILS = 4
NAME = 7
CUSTOMER_ID = 1
CHECK = 6


for row in csv.reader(sys.stdin):
    if row[DETAILS] != 'customer':
        continue
    assert row[CUSTOMER_ID] == row[CHECK], row
