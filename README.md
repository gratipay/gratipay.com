# Welcome to Gratipay [<img height="26px" src="https://raw.githubusercontent.com/gratipay/gratipay.com/master/www/assets/gratipay.opengraph.png"/>](https://gratipay.com/)

[![Build Status](http://img.shields.io/travis/gratipay/gratipay.com/master.svg)](https://travis-ci.org/gratipay/gratipay.com)
[![Open Bounties](https://api.bountysource.com/badge/team?team_id=423&style=bounties_received)](https://www.bountysource.com/teams/gratipay/issues)

[Gratipay](http://gratipay.com) helps companies fund open source,
in order to cultivate an economy of gratitude, generosity, and love.


# Documentation

| Scope  | Location |
|:-------|:------|
| **product**<br>*customer-facing pages* | https://gratipay.com/about |
| **company**<br>*policies, procedures, etc.* | http://inside.gratipay.com |
| **software** | http://gratipay.readthedocs.io/ |
| **installation** | You're there! Read on ... |


Quick Start
===========

Local
-----

Given Python 2.7, Postgres 9.3, and a C/make toolchain:

```shell
git clone git@github.com:gratipay/gratipay.com.git
cd gratipay.com
scripts/bootstrap-debian.sh
make schema data
```

And then run

```shell
make run
```

to boot the app and/or:

```shell
make test
```

to run the tests.

[Read more](#table-of-contents).


Vagrant
-------

Given VirtualBox 4.3 and Vagrant 1.7.x:

```shell
vagrant up
```

[Read more](#vagrant-1).


Docker
-------

Given some version(?) of Docker:

```shell
docker build -t gratipay .
docker run -p 8537:8537 gratipay
```

[Read more](#docker-1).


Table of Contents
=================

 - [Installing](#installing)
  - [Dependencies](#dependencies)
  - [Building](#building)
  - [Launching](#launching)
  - [Configuring](#configuring)
  - [Vagrant](#vagrant)
  - [Docker](#docker)
  - [Help!](#help)
 - [Modifying CSS and Javascript](#modifying-css-and-javascript)
 - [Modifying the Database](#modifying-the-database)
 - [Testing](#testing-)
 - [Setting up a Database](#local-database-setup)
 - [API](#api)
  - [Implementations](#api-implementations)
 - [Glossary](#glossary)


Installing
==========

Thanks for hacking on Gratipay! Be sure to review
[CONTRIBUTING](https://github.com/gratipay/gratipay.com/blob/master/CONTRIBUTING.md#readme)
as well if that's what you're planning to do.


Dependencies
------------

Building `gratipay.com` requires [Python
2.7](http://python.org/download/releases/2.7.4/), and a gcc/make toolchain.

All Python library dependencies are bundled in the repo (under `vendor/`). If
you are receiving issues from `psycopg2`, please [ensure that its needs are
met](http://initd.org/psycopg/docs/faq.html#problems-compiling-and-deploying-psycopg2).

On Debian or Ubuntu you will need the following packages:

```shell
sudo apt-get install postgresql-9.3 postgresql-contrib libpq-dev python-dev libffi-dev libssl-dev
```

On OS X you can [download Postgres directly](http://www.postgresql.org/download/macosx/) or install through [Homebrew](http://brew.sh/):

```shell
brew install postgresql
```

To configure local Postgres create default role (if it hasn’t been created already) and database.

```shell
sudo -u postgres createuser --superuser $USER
createdb gratipay
```

If you are getting an error about `unknown argument: '-mno-fused-madd'` when
running `make`, then add
`Wno-error=unused-command-line-argument-hard-error-in-future` to your
`ARCHFLAGS` environment variable and run `make clean env` again (see [this Stack Overflow answer
for more information](http://stackoverflow.com/a/22355874/347246)):

```shell
ARCHFLAGS=-Wno-error=unused-command-line-argument-hard-error-in-future make clean env
```


Building
--------

All Python dependencies (including virtualenv) are bundled with Gratipay in the
vendor/ directory. Gratipay is designed so that you don't manage its
virtualenv directly and you don't download its dependencies at build
time.

The included `Makefile` contains several targets. Configuration options
are stored in default_local.env file while overrides are in local.env.

To create virtualenv enviroment with all python dependencies installed
in a sandbox:

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

```shell
$ make run
PATH=env/bin:{lots-more-of-your-own-PATH} env/bin/honcho run -e defaults.env,local.env web
2014-07-22 14:53:09 [1258] [INFO] Starting gunicorn 18.0
2014-07-22 14:53:09 [1258] [INFO] Listening at: http://0.0.0.0:8537 (1258)
2014-07-22 14:53:09 [1258] [INFO] Using worker: sync
2014-07-22 14:53:09 [1261] [INFO] Booting worker with pid: 1261
pid-1261 thread-140735191843600 (MainThread) Reading configuration from defaults, environment, and command line.
pid-1261 thread-140735191843600 (MainThread)   changes_reload         False                          default
pid-1261 thread-140735191843600 (MainThread)   changes_reload         True                           environment variable ASPEN_CHANGES_RELOAD=yes
pid-1261 thread-140735191843600 (MainThread)   charset_dynamic        UTF-8                          default
pid-1261 thread-140735191843600 (MainThread)   charset_static         None                           default
pid-1261 thread-140735191843600 (MainThread)   configuration_scripts  []                             default
pid-1261 thread-140735191843600 (MainThread)   indices                [u'index.html', u'index.json', u'index', u'index.html.spt', u'index.json.spt', u'index.spt'] default
pid-1261 thread-140735191843600 (MainThread)   list_directories       False                          default
pid-1261 thread-140735191843600 (MainThread)   logging_threshold      0                              default
pid-1261 thread-140735191843600 (MainThread)   media_type_default     text/plain                     default
pid-1261 thread-140735191843600 (MainThread)   media_type_json        application/json               default
pid-1261 thread-140735191843600 (MainThread)   project_root           None                           default
pid-1261 thread-140735191843600 (MainThread)   project_root           .                              environment variable ASPEN_PROJECT_ROOT=.
pid-1261 thread-140735191843600 (MainThread)   renderer_default       stdlib_percent                 default
pid-1261 thread-140735191843600 (MainThread)   show_tracebacks        False                          default
pid-1261 thread-140735191843600 (MainThread)   show_tracebacks        True                           environment variable ASPEN_SHOW_TRACEBACKS=yes
pid-1261 thread-140735191843600 (MainThread)   www_root               None                           default
pid-1261 thread-140735191843600 (MainThread)   www_root               www/                           environment variable ASPEN_WWW_ROOT=www/
pid-1261 thread-140735191843600 (MainThread) project_root is relative to CWD: '.'.
pid-1261 thread-140735191843600 (MainThread) project_root set to /Users/whit537/personal/gratipay/gratipay.com.
pid-1261 thread-140735191843600 (MainThread) Found plugin for renderer 'jinja2'
pid-1261 thread-140735191843600 (MainThread) Won't log to Sentry (SENTRY_DSN is empty).
pid-1261 thread-140735191843600 (MainThread) Renderers (*ed are unavailable, CAPS is default):
pid-1261 thread-140735191843600 (MainThread)   stdlib_percent
pid-1261 thread-140735191843600 (MainThread)   json_dump
pid-1261 thread-140735191843600 (MainThread)   stdlib_format
pid-1261 thread-140735191843600 (MainThread)   JINJA2
pid-1261 thread-140735191843600 (MainThread)   stdlib_template
```

You should then find this in your browser at
[http://localhost:8537/](http://localhost:8537/):

![Success](https://raw.github.com/gratipay/gratipay.com/master/img-src/success.png)

Congratulations! Sign in using Twitter or GitHub and you're off and
running. At some point, try [running the test suite](#testing-).

Configuring
-----------

Gratipay's default configuration lives in [`defaults.env`](https://github.com/gratipay/gratipay.com/blob/master/defaults.env).
If you'd like to override some settings, create a file named `local.env` to store them.

The following explains some of the content of that file:

The `GITHUB_*` keys are for a gratipay-dev application in the Gratipay
organization on Github. It points back to localhost:8537, which is where
Gratipay will be running if you start it locally with `make run`. Similarly
with the `TWITTER_*` keys, but there they required us to spell it `127.0.0.1`.

If you are running Gratipay somewhere other than `localhost:8537`, then you'll
need to set `BASE_URL`, but your options are limited because we use proprietary
fonts from [Typography.com](http://www.typography.com/), and they filter by
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


Vagrant
-------
Vagrant provides a convenient interface to VirtualBox to run and test
Gratipay in virtual machine. This may be handy if you're on Windows.

You will need [Vagrant](http://www.vagrantup.com/) and [VirtualBox](https://www.virtualbox.org/)
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

Docker
------------

You can also install/run Gratipay with Docker.

Build it with the included Dockerfile:

```shell
$ git clone git@github.com:gratipay/gratipay.com.git
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

Help!
-----

If you get stuck somewhere along the way, [make an
issue](https://github.com/gratipay/gratipay.com/issues/new) here on GitHub.

Thanks for installing Gratipay! :smiley:


Modifying CSS and JavaScript
============================

We use SCSS, with files stored in `scss/`. All of the individual files are
combined in `scss/gratipay.scss` which itself is compiled by `libsass` in
[`www/assets/gratipay.css.spt`](https://github.com/gratipay/gratipay.com/blob/master/www/assets/gratipay.css.spt)
on each request (it's behind a CDN in production).

We use a similar pattern for JavaScript. Individual files are in `js/`, and
they're concatenated on the fly (and put behind a CDN in production) in
[`www/assets/gratipay.js.spt`](https://github.com/gratipay/gratipay.com/blob/master/www/assets/gratipay.js.spt)


Modifying the Database
======================

We write SQL, specifically the [PostgreSQL
variant](http://www.postgresql.org/docs/9.3/static/). We keep our database
schema in
[`schema.sql`](https://github.com/gratipay/gratipay.com/blob/master/sql/schema.sql),
and we write schema changes for each PR branch in a `sql/branch.sql` file, which
then gets run against production and merged into `sql/schema.sql` during
deployment.


Testing [![Build Status](http://img.shields.io/travis/gratipay/gratipay.com/master.svg)](https://travis-ci.org/gratipay/gratipay.com)
=======

Our test suite is divided into through-the-web (TTW) tests and Python tests.
You need to install [PhantomJS](http://phantomjs.org/) separately in order to
run the TTW tests. For both suites we use the [pytest](http://pytest.org/) test
runner; it's installed automatically as part of `make env`.

The easiest way to run the whole test suite is:

```shell
make test
```

You can also do:

```shell
make ttwtest
```

and/or:

```shell
make pytest
```

To invoke `py.test` directly you should use the `honcho` utility that comes
with the install. First `make tests/env`, the activate the virtualenv by running
`source env/bin/activate`, and then:

    [gratipay] $ cd tests/
    [gratipay] $ honcho run -e defaults.env,local.env py.test

Be careful! The test suite deletes data in all tables in the public schema of the
database configured in your testing environment.


Local Database Setup
--------------------

For the best development experience, you need a local
installation of [Postgres](http://www.postgresql.org/download/). The best
version of Postgres to use is 9.3.5, because that's what we're using in
production at Heroku. You need at least 9.2, because we depend on being able to
specify a URI to `psql`, and that was added in 9.2.

+ Mac: use Homebrew: `brew install postgres`
+ Ubuntu: use Apt: `apt-get install postgresql postgresql-contrib libpq-dev`

To setup the instance for gratipay's needs run:

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

Which populates the database named by `DATABASE_URL` with the schema from `sql/schema.sql`.

### Example data

The gratipay database created in the last step is empty. To populate it with
some fake data, so that more of the site is functional, run this command:

```shell
make fake
```


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

**[/about/stats.json](https://gratipay.com/about/stats.json)**
([source](https://github.com/gratipay/gratipay.com/tree/master/www/about/stats.spt))&mdash;<i>public</i>&mdash;Returns
an object giving a point-in-time snapshot of Gratipay. The
[stats](https://gratipay.com/about/stats.html) page displays the same info.

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
========

Gratipay is dedicated to public domain. See the text of [CC0 1.0 Universal](http://creativecommons.org/publicdomain/zero/1.0/) dedication in [COPYING](COPYING) here.
