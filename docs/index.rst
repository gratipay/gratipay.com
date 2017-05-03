gratipay.com
==============

Welcome! This is the documentation for programmers working on `gratipay.com`_
(not to be confused with programmers working with Gratipay's `web API`_).

.. _gratipay.com: https://github.com/gratipay/gratipay.com
.. _web API: https://github.com/gratipay/gratipay.com#api


.. _db-schema:

DB Schema
---------

Users
^^^^^

``is_suspicious`` on a participant can be ``None`` (unknown), ``True``
(blacklisted) or ``False`` (whitelisted)

    * whitelisted can transfer money out of gratipay
    * unknown can move money within gratipay
    * blacklisted cannot do anything

Money
^^^^^

- ``transfers``

Used under Gratipay 1.0, when users were allowed to tip each other (without
having to setup a team). ``transfers`` models money moving **within** Gratipay,
from one participant (``tipper``) to another (``tippee``).

- ``payments``

The replacement for ``transfers``, used in Gratipay 2.0. ``payments`` are
between a Team and a Participant, in either direction (``to-team``, or
``to-participant``)

- ``exchanges``

Records money moving into and out of Gratipay. Every ``exchange`` is linked to a
participant. The ``amount`` column shows a positive amount for money flowing
into gratipay (payins), and a negative amount for money flowing out of Gratipay
(payouts). The ``fee`` column is always positive. For both payins and payouts,
the ``amount`` does not include the ``fee`` (e.g., a $10 payin would result in
an ``amount`` of ``9.41`` and a ``fee`` of ``0.59``, and a $100 payout with a
2% fee would result in an ``amount`` of ``-98.04`` and a fee of ``1.96``).

Contents
--------

.. toctree::
    :maxdepth: 2

    gratipay Python library <gratipay>
