gratipay.com
==============

Welcome! This is the documentation for programmers working on `gratipay.com`_
(not to be confused with programmers working with Gratipay's `web API`_).

.. _gratipay.com: https://github.com/gratipay/gratipay.com
.. _web API: https://github.com/gratipay/gratipay.com#api


DB Schema
---------

You should think of Gratipay as a PostgreSQL application, because Postgres is
our data store, and we depend heavily on it. We write SQL. We use Postgres
features. We have our own Postgres library for Python. If you want to
understand Gratipay, you should start by understanding our schema.

There are three main parts to our schema:

 - The ``journal``. Gratipay implements a full-fledged double-entry accounting
   system, and the ``journal`` table is at the heart of it.

 - **~user**-related tables. The primary table for users is ``participants``.
   A number of other tables record additional information related to users,
   such as accounts elsewhere (``accounts_elsewhere``), and payment routes
   (``exchange_routes``).

 - **Team**-related tables. The primary table for Teams is ``teams``. The
   ``subscriptions`` and ``payroll`` tables record recurring payments to and
   takes from Teams, respectively.

We also have an ``email_queue`` table for outbound mail, and the weekly payday
process generates several temporary tables, prefixed with ``payday_``. In
addition to these tables, we have a number of views, all prefixed with
``current_``.

One pattern to watch for: three-state booleans. We sometimes use ``NULL`` with
``boolean`` to represent an unknown state, e.g., with
``participants.is_suspicious``


Contents
--------

.. toctree::
    :maxdepth: 2

    gratipay Python library <gratipay>
