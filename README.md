# <img alt="Welcome to Gratipay" src="https://raw.githubusercontent.com/gratipay/gratipay.com/master/img-src/readme-banner.png"/>

[Gratipay](https://gratipay.com) helps companies pay for open source, in order to
[cultivate](http://inside.gratipay.com/big-picture/mission) an economy of
gratitude, generosity, and love.


| Scope  | Documentation |
|:-------|:------|
| **company**<br>*policies, procedures, etc.* | http://inside.gratipay.com |
| **product**<br>*customer-facing pages* | https://gratipay.com/about |
| **software installation** | &larr; You are here! |
| **python library** | https://gratipay.readthedocs.io/ |


Table of Contents
=================

- [Quick Start](#quick-start)
- [Installing](#installing)
  - [Satisfying Dependencies](#satisfying-dependencies)
  - [Setting up a Database](#setting-up-a-database)
  - [Building](#building)
  - [Launching](#launching)
  - [Help!](#help)
- [Installing with Vagrant](#installing-with-vagrant)
- [Installing with Docker](#installing-with-docker)
- [Configuring](#configuring)
- [Developing](#developing)
  - [Codebase Overview](#codebase-overview)
  - [Modifying CSS and JavaScript](#modifying-css-and-javascript)
  - [Modifying the Database](#modifying-the-database)
- [Testing](#testing-)
- [API](#api)
  - [Implementations](#api-implementations)
- [Glossary](#glossary)
- [License](#license)


Quick Start
===========

Thanks for hacking on Gratipay! Be sure to review
[CONTRIBUTING](https://github.com/gratipay/gratipay.com/blob/master/CONTRIBUTING.md#readme)
as well if that's what you're planning to do.

Unix-like
---------

Given Python 2.7, Postgres 9.6, and a C/make toolchain:

```shell
git clone https://github.com/gratipay/gratipay.com.git
cd gratipay.com
createdb gratipay
make schema fake
```

Now `make run` to [boot the app](#launching) or `make test` to [run the
tests](#testing).

[Read more](#installing).


Vagrant
-------

Given VirtualBox 4.3 and Vagrant 1.7.x:

```shell
vagrant up
```

[Read more](#installing-with-vagrant).


Docker
------

Given some version(?) of Docker:

```shell
docker build -t gratipay .
docker run -p 8537:8537 gratipay
```

[Read more](#installing-with-docker).


Installing
==========

Satisfying Dependencies
-----------------------

Building, launching, developing and testing `gratipay.com` requires several pieces of software:

- a C/make toolchain,
- [Python](https://www.python.org/) version 2.7,
- [Postgres](https://www.postgresql.org/) version 9.6, and
- [Firefox](https://www.mozilla.org/en-US/firefox/new/) and
  [geckodriver](https://github.com/mozilla/geckodriver/releases/) for
[testing](#testing-).


Unix-like operating systems (Ubuntu, macOS, etc.) generally include a C/make
toolchain. If you're on Windows, your best bet is to use
[Vagrant](#installing-with-vagrant) or [Docker](#installing-with-docker).

All Python dependencies are bundled in our repo (under
[`vendor/`](https://github.com/gratipay/gratipay.com/tree/master/vendor)), but
some include C extensions with additional operating-system level dependencies
that need to be met. Here are [notes for
`psycopg2`](http://initd.org/psycopg/docs/faq.html#problems-compiling-and-deploying-psycopg2).
Other candidates for trouble are `libsass` and `cryptography`. Good luck!

### Debian/Ubuntu

Maybe try [`scripts/bootstrap-debian.sh`](https://github.com/gratipay/gratipay.com/tree/master/scripts/bootstrap-debian.sh)?

### macOS

If `make env` gives you an `Operation not permitted` error from
`shutil.copytree` then you're probably using the system Python and you should
try [Homebrew](https://brew.sh/) instead:

```shell
brew install python
```

Here are the [installation options for
Postgres](https://www.postgresql.org/download/macosx/).

If you are getting an error about `unknown argument: '-mno-fused-madd'` when
running `make`, then add
`Wno-error=unused-command-line-argument-hard-error-in-future` to your
`ARCHFLAGS` environment variable and run `make clean env` again (see [this Stack Overflow answer
for more information](https://stackoverflow.com/a/22355874/347246)):

```shell
ARCHFLAGS=-Wno-error=unused-command-line-argument-hard-error-in-future make clean env
```


Setting up a Database
---------------------

The best version of Postgres to use is 9.6.2, because that's what we're using
in production at Heroku. You need at least 9.5 to support the features we
depend on, along with the `pg_stat_statements` and `pg_trgm` extensions.

To setup Postgres for Gratipay's needs run:

```shell
sudo -u postgres createuser --superuser $USER
createdb gratipay
createdb gratipay-test
```

You can speed up the test suite when using a regular HDD by running:

```shell
psql -q gratipay-test -c 'alter database "gratipay-test" set synchronous_commit to off'
```

### Schema

Once Postgres is set up, run:

```shell
make schema
```

Which populates the database [named](#configuring) by `DATABASE_URL` with the
schema from `sql/schema.sql`.

### Example data

The `gratipay` database created in the last step is empty. To populate it with
some fake data, so that more of the site is functional, run this command:

```shell
make fake
```


Building
--------

All Python dependencies (including virtualenv) are bundled with Gratipay in the
`vendor/` directory. Gratipay is designed so that you don't manage its
virtualenv (a Python-specific sandboxing mechanism) directly and you don't
download its dependencies at build time but rather at clone time.  To create a
virtualenv with all Python dependencies installed:

```shell
make env
```

If you haven't run Gratipay for a while, you can reinstall the dependencies:

```shell
make clean env
```

Add the necessary schemas and insert dummy data into postgres:

```shell
make schema
make fake
```


Launching
---------

Once you've installed Python and Postgres and set up a database, you can use
make to build and launch Gratipay:

```shell
make run
```

If you don't have make, look at the Makefile to see what steps you need
to perform to build and launch Gratipay. The Makefile is pretty simple and
straightforward.

If Gratipay launches successfully it will look like this:

```
$ make run
PATH=env/bin:{lots-more-of-your-own-PATH} env/bin/honcho run -e defaults.env,local.env web
[2017-08-25 15:05:18 -0400] [18093] [INFO] Starting gunicorn 19.7.1
[2017-08-25 15:05:18 -0400] [18093] [INFO] Listening at: http://0.0.0.0:8537 (18093)
[2017-08-25 15:05:18 -0400] [18093] [INFO] Using worker: sync
[2017-08-25 15:05:18 -0400] [18096] [INFO] Booting worker with pid: 18096
pid-18096 thread-140736833041344 (MainThread) Instantiating Application from gunicorn_entrypoint
pid-18096 thread-140736833041344 (MainThread) Reading configuration from defaults, environment, and kwargs.
pid-18096 thread-140736833041344 (MainThread)   base_url                                              default                 
pid-18096 thread-140736833041344 (MainThread)   changes_reload         False                          default                 
pid-18096 thread-140736833041344 (MainThread)   changes_reload         True                           environment variable ASPEN_CHANGES_RELOAD=yes
pid-18096 thread-140736833041344 (MainThread)   charset_dynamic        UTF-8                          default                 
pid-18096 thread-140736833041344 (MainThread)   charset_static         None                           default                 
pid-18096 thread-140736833041344 (MainThread)   colorize_tracebacks    True                           default                 
pid-18096 thread-140736833041344 (MainThread)   indices                [u'index.html', u'index.json', u'index', u'index.html.spt', u'index.json.spt', u'index.spt'] default                 
pid-18096 thread-140736833041344 (MainThread)   list_directories       False                          default                 
pid-18096 thread-140736833041344 (MainThread)   logging_threshold      0                              default                 
pid-18096 thread-140736833041344 (MainThread)   media_type_default     text/plain                     default                 
pid-18096 thread-140736833041344 (MainThread)   media_type_json        application/json               default                 
pid-18096 thread-140736833041344 (MainThread)   project_root           None                           default                 
pid-18096 thread-140736833041344 (MainThread)   project_root           .                              environment variable ASPEN_PROJECT_ROOT=.
pid-18096 thread-140736833041344 (MainThread)   renderer_default       stdlib_percent                 default                 
pid-18096 thread-140736833041344 (MainThread)   show_tracebacks        False                          default                 
pid-18096 thread-140736833041344 (MainThread)   show_tracebacks        True                           environment variable ASPEN_SHOW_TRACEBACKS=yes
pid-18096 thread-140736833041344 (MainThread)   www_root               None                           default                 
pid-18096 thread-140736833041344 (MainThread)   www_root               www/                           environment variable ASPEN_WWW_ROOT=www/
pid-18096 thread-140736833041344 (MainThread) project_root is relative to CWD: '.'.
pid-18096 thread-140736833041344 (MainThread) project_root set to /Users/whit537/personal/gratipay/gratipay.com.
pid-18096 thread-140736833041344 (MainThread) Found plugin for renderer 'jinja2'
pid-18096 thread-140736833041344 (MainThread) Renderers (*ed are unavailable, CAPS is default):
pid-18096 thread-140736833041344 (MainThread)   json_dump        
pid-18096 thread-140736833041344 (MainThread)   jsonp_dump       
pid-18096 thread-140736833041344 (MainThread)   stdlib_template  
pid-18096 thread-140736833041344 (MainThread)   stdlib_format    
pid-18096 thread-140736833041344 (MainThread)   jinja2           
pid-18096 thread-140736833041344 (MainThread)   STDLIB_PERCENT   
pid-18096 thread-140736833041344 (MainThread) Won't log to Sentry (SENTRY_DSN is empty).
pid-18096 thread-140736833041344 (MainThread) AWS SES is not configured! Mail will be dumped to the console here.
pid-18096 thread-140736833041344 (MainThread) Cron: not installing update_cta.
pid-18096 thread-140736833041344 (MainThread) Cron: not installing self_check.
pid-18096 thread-140736833041344 (MainThread) Cron: not installing <lambda>.
pid-18096 thread-140736833041344 (MainThread) Cron: not installing flush.
pid-18096 thread-140736833041344 (MainThread) Cron: not installing log_metrics.
```

You should then find this in your browser at
[http://localhost:8537/](http://localhost:8537/):

![Success](https://raw.github.com/gratipay/gratipay.com/master/img-src/success.png)

Congratulations! Now enter a dollar amount [less than
2000](https://developers.braintreepayments.com/reference/general/testing/python#test-amounts)
(ironically), and submit the form to complete the basic flow:

![More Success](https://raw.github.com/gratipay/gratipay.com/master/img-src/more-success.png)

You're off and running! At some point, try [running the test suite](#testing-).


Help!
-----

If you get stuck somewhere along the way, [make an
issue](https://github.com/gratipay/gratipay.com/issues/new) here on GitHub.

Thanks for installing Gratipay! :smiley:


Installing with Vagrant
=======================

Vagrant provides a convenient interface to VirtualBox to run and test
Gratipay in virtual machine. This may be handy if you're on Windows.

You will need [Vagrant](https://www.vagrantup.com/) and [VirtualBox](https://www.virtualbox.org/)
installed. On Linux you may need to install `nfs-kernel-server` as well.

With Vagrant, you can run Gratipay by running `vagrant up` from the project
directory. Please note that if you ever switch between running Gratipay on your
own machine to Vagrant or vice versa, you will need to run `make clean`.

The `Vagrantfile` will download a pristine Ubuntu image (base box), save it,
and create a virtual machine (VM) in VirtualBox. Then it will set up Gratipay
prerequisites (the process is known as "provisioning") and show a welcome message.

The next time you run `vagrant up`, it will reuse the VM. Vagrant uses SSH
based authentication. To login to VM, use the `vagrant ssh` command. If you're
prompted for a password when logging in, please use `vagrant`.

**Mac users:** If you're prompted for a password during initial installation,
it's sudo and you should enter your Mac OS password.

**Ubuntu users:** If you experience problems, please see [this
issue](https://github.com/gratipay/gratipay.com/pull/2321#issuecomment-41455169).
As mentioned there, you will also need to be wary of projects that are nested
in encrypted directories.


Installing with Docker
======================

You can also install/run Gratipay with Docker.

Build it with the included Dockerfile:

```shell
$ git clone https://github.com/gratipay/gratipay.com.git
$ cd gratipay.com
$ docker build -t gratipay .
```

Once you've built the image, you can launch a container:


```shell
$ docker run -d -p 8537:8537 gratipay
```

Check it out at [localhost:8537](http://localhost:8537/)!


To edit files and have those changes reflect in the running container, mount your local folder when you execute the run command:

```shell
$ docker run -d -v $PWD:/srv/gratipay.com -p 8537:8537 gratipay
```

You can get the running container's ID with `docker ps`. With that, you can

- view the logs:

```shell
$ docker logs [container_id]
```

- run commands within the project root:

```shell
$ docker exec [container_id] make schema
$ docker exec [container_id] make fake
```

Once you're done, kill the running container:

```shell
$ docker kill [container_id]
```


Configuring
===========

Gratipay's default configuration lives in [`defaults.env`](https://github.com/gratipay/gratipay.com/blob/master/defaults.env).
If you'd like to override some settings, create a file named `local.env` to store them.

The following explains some of the content of that file:

The `GITHUB_*` keys are for a gratipay-dev application in the Gratipay
organization on Github. It points back to localhost:8537, which is where
Gratipay will be running if you start it locally with `make run`. Similarly
with the `TWITTER_*` keys, but there they required us to spell it `127.0.0.1`.

If you are running Gratipay somewhere other than `localhost:8537`, then you'll
need to set `BASE_URL`, but your options are limited because we use proprietary
fonts from [Typography.com](https://www.typography.com/), and they filter by
`Referer`. You won't get the right fonts unless you use an approved domain.
We've configured `gratipay.dev` as well as `localhost`, so if you don't want to
run on `localhost` then configure `gratipay.dev` in your
[`/etc/hosts`](https://en.wikipedia.org/wiki/Hosts_(file)) file and set this in
`local.env`:

    BASE_URL=http://gratipay.dev:8537
    GITHUB_CLIENT_ID=ca4a9a35c161af1d024d
    GITHUB_CLIENT_SECRET=8744f6333d51b5f4af38d46cf035ecfcf34c671e
    GITHUB_CALLBACK=http://gratipay.dev:8537/on/github/associate

If you wish to use a different username or database name for the database, you
should override the `DATABASE_URL` in `local.env` using the following format:

    DATABASE_URL=postgres://<username>@localhost/<database name>

We use Amazon Web Services' Simple Email Service (AWS SES) for sending emails.
In development, we dump outbound mail to the console by default. This is fine
if all you need to do is, e.g., copy/paste verification links. If you need to
receive emails within a proper mail client during development, then sign up for
[AWS's free tier](https://aws.amazon.com/free) and override the `AWS_*`
credentials from `defaults.env` in your `local.env`. You'll have to verify the
email addresses you want to receive email with on SES.


Developing
==========

Codebase Overview
-----------------

| Directory               | Frontend | Backend  | Description |
|:------------------------|:--------:|:--------:|:------------|
| `www`                   | &#x2705; |          | web requests land here, e.g., https://gratipay.com/on/npm/express hits [`www/on/npm/%platform.spt`](https://github.com/gratipay/gratipay.com/blob/master/www/on/npm/%25package.spt) (a [simplate](http://simplates.org/)) |
| `js`<br>`scss`          | &#x2705; |          | JavaScript (w/ jQuery) and [SCSS](http://sass-lang.com/documentation/file.SCSS_FOR_SASS_USERS.html) files, dynamically pipelined via endpoints at [`www/assets/gratipay.js.spt`](https://github.com/gratipay/gratipay.com/blob/master/www/assets/gratipay.js.spt) and [`.css.spt`](https://github.com/gratipay/gratipay.com/blob/master/www/assets/gratipay.css.spt) |
| `templates`<br>`emails` | &#x2705; |          | templating files for web and email, respectively, using [Jinja](http://jinja.pocoo.org/) |
| `gratipay`              |          | &#x2705; | a Python library with app wiring, models, and business logic |
| `sql`                   |          | &#x2705; | SQL files, the main one is `schema.sql`, changes go in a `branch.sql`, but there's also lots of raw SQL in Python strings throughout `gratipay` and even `www` |
| `tests`                 | &#x2705; | &#x2705; | test scripts, `tests/ttw` run "through the web" on a real browser, `tests/py` simulate HTTP calls and exercise Python APIs |
| `gratipay/testing`     | &#x2705; | &#x2705; | submodule for infrastructure used by test scripts |


Modifying CSS and JavaScript
----------------------------

We use
[SCSS](http://sass-lang.com/documentation/file.SCSS_FOR_SASS_USERS.html), with
files stored in `scss/`. All of the individual files are combined in
`scss/gratipay.scss` which itself is compiled by `libsass` in
[`www/assets/gratipay.css.spt`](https://github.com/gratipay/gratipay.com/blob/master/www/assets/gratipay.css.spt)
on each request (it's behind a CDN in production).

We use a similar pattern for JavaScript. Individual files are in `js/`, and
they're concatenated on the fly (and put behind a CDN in production) in
[`www/assets/gratipay.js.spt`](https://github.com/gratipay/gratipay.com/blob/master/www/assets/gratipay.js.spt).


Modifying the Database
----------------------

We write SQL, specifically the [PostgreSQL
variant](https://www.postgresql.org/docs/9.6/static/). To make schema or data
changes, use [deploy
hooks](https://github.com/gratipay/gratipay.com/blob/master/deploy/#readme).


Testing [![Build Status](http://img.shields.io/travis/gratipay/gratipay.com/master.svg)](https://travis-ci.org/gratipay/gratipay.com)
=======

Run Gratipay's test suite with:

```shell
make test
```

This invokes the [pyflakes](https://pypi.python.org/pypi/pyflakes) linter and
then the [pytest](http://pytest.org/) test runner with four layers of
[configuration](#configuring) (last wins): `defaults.env`, `local.env`,
`tests/defaults.env`, `tests/local.env`. To run a subset of the test suite or
otherwise influence the test run, pass arguments to `py.test` using an `ARGS`
environment variable like so:

```shell
ARGS="tests/py/test_billing_payday.py -k notify -vvv" make test
```

The tests in `tests/ttw` ("through the web") require
[Firefox](https://www.mozilla.org/en-US/firefox/new/) and
[geckodriver](https://github.com/mozilla/geckodriver/releases/). The tests in
`tests/py` do not.

Be careful! The test suite deletes data in all tables in the public schema of the
database configured in your testing environment.


API
===

The Gratipay API is comprised of these four endpoints:

**[/about/charts.json](https://gratipay.com/about/charts.json)**
([source](https://github.com/gratipay/gratipay.com/tree/master/www/about/charts.json.spt))&mdash;<i>public</i>&mdash;Returns
an array of objects, one per week, showing aggregate numbers over time. The
[stats](https://gratipay.com/about/stats) page uses this.

**[/about/paydays.json](https://gratipay.com/about/paydays.json)**
([source](https://github.com/gratipay/gratipay.com/tree/master/www/about/paydays.json.spt))&mdash;<i>public</i>&mdash;Returns
an array of objects, one per week, showing aggregate numbers over time. The old
charts page used to use this.

**/`~username`/public.json**
([example](https://gratipay.com/Gratipay/public.json),
[source](https://github.com/gratipay/gratipay.com/blob/master/www/~/%25username/public.json.spt))&mdash;<i>public</i>&mdash;Returns an object with these keys:

  - "taking"&mdash;an estimate of the amount the given participant will
    take from Teams this week

  - "elsewhere"&mdash;participant's connected accounts elsewhere; returns an object with these keys:

      - "bitbucket"&mdash;participant's Bitbucket account; possible values are:
          - `undefined` (key not present)&mdash;no Bitbucket account connected
          - `https://bitbucket.org/api/1.0/users/%bitbucket_username`
      - "github"&mdash;participant's GitHub account; possible values are:
          - `undefined` (key not present)&mdash;no GitHub account connected
          - `https://api.github.com/users/%github_username`
      - "twitter"&mdash;participant's Twitter account; possible values are:
          - `undefined` (key not present)&mdash;no Twitter account connected
          - `https://api.twitter.com/1.1/users/show.json?id=%twitter_immutable_id&include_entities=1`
      - "openstreetmap"&mdash;participant's OpenStreetMap account; possible values are:
          - `undefined` (key not present)&mdash;no OpenStreetMap account connected
          - `http://www.openstreetmap.org/user/%openstreetmap_username`

**/`~username`/payment-instructions.json**
([source](https://github.com/gratipay/gratipay.com/blob/master/www/~/%25username/payment-instructions.json.spt))&mdash;*private*&mdash;Responds
to `GET` with an array of objects representing your current payment
instructions. A payment instruction is created when a ~user instructs Gratipay
to make voluntary payments to a Team. Pass a `team_slug` with `GET` to fetch
payment instruction only for that particular team. `POST` an array of objects
containing `team_slug` and `amount` to bulk upsert payment instructions (make
sure to set `Content-Type` to `application/json`). The `amount` must be encoded
as a string rather than a number. In case the upsert is not successful for any
object, there will be an `error` attribute in the response explaining the error
along with the `team_slug` to identify the object for which the error occurred.

This endpoint requires authentication. Look up your user ID and API key on your
[account page](https://gratipay.com/about/me/settings/) and pass them using
basic auth.

E.g.:
Request

```
curl https://gratipay.com/~username/payment-instructions.json \
    -u $userid:$api_key \
    -X POST \
    -d '[{"amount": "1.00", "team_slug": "foobar"}]' \
    -H "Content-Type: application/json"
```

Response

```
[
    {
        "amount": "1.00",
        "ctime": "2016-01-30T12:38:00.182230+00:00",
        "due": "0.00",
        "mtime": "2016-02-06T14:37:28.532508+00:00",
        "team_name": "Foobar team",
        "team_slug": "foobar"
    }
]
```

API Implementations
-------------------

Below are some projects that use the Gratipay APIs, that can serve as inspiration
for your project!

### Renamed to Gratipay

 - [Ruby: gratitude](https://github.com/JohnKellyFerguson/gratitude): a simple
   ruby wrapper for the Gratipay API

 - [php-curl-class](https://github.com/php-curl-class/php-curl-class/blob/master/examples/gratipay_send_tip.php): a php class to tip using the Gratipay API

 - [gratipay-twisted](https://github.com/TigerND/gratipay-twisted): Gratipay client
   for the Twisted framework

 - [WordPress: WP-Gratipay](https://github.com/KakersUK/WP-Gratipay): a simple way to show a Gratipay widget on your WordPress site


### Still Using Gittip

These probably still work, but are using our [old name](https://medium.com/gratipay-blog/gratitude-gratipay-ef24ad5e41f9):

 - [Drupal: Gittip](https://drupal.org/project/gittip): Includes a Gittip
   giving field type to let you implement the Khan academy model for users on
   your Drupal site. ([ticket](https://www.drupal.org/node/2332131))

 - [Node.js: Node-Gittip](https://npmjs.org/package/gittip) (also see [Khan
   Academy's setup](http://ejohn.org/blog/gittip-at-khan-academy/)) ([ticket](https://github.com/KevinTCoughlin/node-gittip/issues/1))

 - [hubot-gittip](https://github.com/myplanetdigital/hubot-gittip): A Hubot
   script for interacting with a shared Gratipay account. ([ticket](https://github.com/myplanetdigital/hubot-gittip/issues/6))

 - [gittip-collab](https://github.com/engineyard/gittip-collab): A Khan-style
   tool for managing a Gittip account as a team. ([ticket](https://github.com/engineyard/gittip-collab/issues/1))

 - [WWW::Gittip](https://metacpan.org/pod/WWW::Gittip): A Perl module
   implementing the Gittip API more or less ([ticket](https://rt.cpan.org/Public/Bug/Display.html?id=101103))


Glossary
========

**Account Elsewhere** - An entity's registration on a platform other than
Gratipay (e.g., Twitter).

**Entity** - An entity.

**Participant** - An entity registered with Gratipay.

**User** - A person using the Gratipay website. Can be authenticated or
anonymous. If authenticated, the user is guaranteed to also be a participant.


License
=======

[MIT](COPYING)
