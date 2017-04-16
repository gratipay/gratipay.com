#!/usr/bin/env python
from __future__ import print_function

import re, requests, os, sys

BALANCED_API_SECRET = os.environ['BALANCED_API_SECRET']


try:
    fp = open(sys.argv[1])
except IndexError:
    fp = sys.stdin


for line in fp:
    line = line.strip()
    m = re.match('^SYNCED .*\((.*?)\).*$', line)
    if m is None:
        continue
    card_id = m.groups()[0]
    response = requests.get( 'https://api.balancedpayments.com/cards/{}'.format(card_id)
                           , auth=(BALANCED_API_SECRET, '')
                            )
    if response.status_code != 200:
        print(response.status_code, response.body)
        continue

    cards = response.json()['cards']
    assert len(cards) == 1
    removed = cards[0]['can_debit'] == False
    if removed:
        print("REMOVED", line.split(None, 1)[1])
        sys.stdout.flush()
