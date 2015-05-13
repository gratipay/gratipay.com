#!/usr/bin/env python
"""Sandbox for exploring the new Payday algorithm.
"""
from __future__ import print_function, unicode_literals

from collections import defaultdict


# Classes

class _Thing(object):
    def __init__(self, name):
        self.name = name
        self.values = list()
    def __setitem__(self, k, v):
        self.values.append((k,v))
    def __repr__(self):
        return(self.name)
    def __str__(self):
        return '\n'.join(['{} {}'.format(repr(k),v) for k,v in self.values])

class Participant(_Thing):
    pass

class Team(_Thing):
    owner = None


# Universe

a, b, c, d, e = [Participant(x) for x in 'abcde']
A, B, C, D, E = [Team(x) for x in 'ABCDE']


# subscriptions

a[A] = 1
a[B] = 1
a[C] = 1
a[E] = 1

b

c[A] = 1
c[C] = 1
c[E] = 1

d[D] = 1

e[D] = 1


# payroll

A[b] = 1
A[c] = 1
A.owner = c

B.owner = c

C.owner = a

D.owner = d

E[c] = 1
E.owner = e


def payday(participants, teams):
    """Given a list of participants and a list of teams, return a list.

    The list we return contains instructions for funds transfer, both card
    captures (positive) and bank deposits (negative).

    """
    t_balances = defaultdict(int)
    p_balances = defaultdict(int)
    p_holding = defaultdict(int)

    for p in participants:
        for t, amount in p.values:
            t_balances[t] += amount
            p_holding[p] += amount

    for t in teams:
        for p, amount in t.values:
            t_balances[t] -= amount
            p_balances[p] += amount

    for t in teams:
        p_balances[t.owner] += t_balances[t]
        t_balances[t] -= t_balances[t]

    assert sum(t_balances.values()) == 0

    return [(p, p_balances[p] - p_holding[p]) for p in participants]


for participant, instruction in payday([a,b,c,d,e], [A,B,C,D,E]):
    print("{} {:2}".format(participant.name, instruction))
