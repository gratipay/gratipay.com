"""Wireup
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import atexit
import fnmatch
import os
import urlparse
from tempfile import mkstemp

import aspen
from aspen.testing.client import Client
from babel.core import Locale
from babel.messages.pofile import read_po
from babel.numbers import parse_pattern
import balanced
import boto3
import braintree
import gratipay
import gratipay.billing.payday
import raven
from environment import Environment, is_yesish
from gratipay.elsewhere import PlatformRegistry
from gratipay.elsewhere.bitbucket import Bitbucket
from gratipay.elsewhere.bountysource import Bountysource
from gratipay.elsewhere.github import GitHub
from gratipay.elsewhere.facebook import Facebook
from gratipay.elsewhere.google import Google
from gratipay.elsewhere.openstreetmap import OpenStreetMap
from gratipay.elsewhere.twitter import Twitter
from gratipay.elsewhere.venmo import Venmo
from gratipay.models.account_elsewhere import AccountElsewhere
from gratipay.models.community import Community
from gratipay.models.country import Country
from gratipay.models.exchange_route import ExchangeRoute
from gratipay.models.participant import Participant
from gratipay.models.participant.mixins import Identity
from gratipay.models.team import Team
from gratipay.models import GratipayDB
from gratipay.security.crypto import EncryptingPacker
from gratipay.utils.emails import compile_email_spt, ConsoleMailer
from gratipay.utils.http_caching import asset_etag
from gratipay.utils.i18n import (
    ALIASES, ALIASES_R, COUNTRIES, LANGUAGES_2, LOCALES,
    get_function_from_rule, make_sorted_dict
)

def base_url(website, env):
    gratipay.base_url = website.base_url = env.base_url

def secure_cookies(env):
    gratipay.use_secure_cookies = env.base_url.startswith('https')

def db(env):
    dburl = env.database_url
    maxconn = env.database_maxconn
    db = GratipayDB(dburl, maxconn=maxconn)

    for model in (AccountElsewhere, Community, Country, ExchangeRoute, Participant, Team):
        db.register_model(model)
    gratipay.billing.payday.Payday.db = db

    return db

def crypto(env):
    keys = [k.encode('ASCII') for k in env.crypto_keys.split()]
    Identity.encrypting_packer = EncryptingPacker(*keys)

def mail(env, project_root='.'):
    if env.aws_ses_access_key_id and env.aws_ses_secret_access_key and env.aws_ses_default_region:
        aspen.log_dammit("AWS SES is configured! We'll send mail through SES.")
        Participant._mailer = boto3.client( service_name='ses'
                                          , region_name=env.aws_ses_default_region
                                          , aws_access_key_id=env.aws_ses_access_key_id
                                          , aws_secret_access_key=env.aws_ses_secret_access_key
                                           )
    else:
        aspen.log_dammit("AWS SES is not configured! Mail will be dumped to the console here.")
        Participant._mailer = ConsoleMailer()
    emails = {}
    emails_dir = project_root+'/emails/'
    i = len(emails_dir)
    for spt in find_files(emails_dir, '*.spt'):
        base_name = spt[i:-4]
        emails[base_name] = compile_email_spt(spt)
    Participant._emails = emails

def billing(env):
    balanced.configure(env.balanced_api_secret)

    if env.braintree_sandbox_mode:
        braintree_env = braintree.Environment.Sandbox
    else:
        braintree_env = braintree.Environment.Production

    braintree.Configuration.configure(
        braintree_env,
        env.braintree_merchant_id,
        env.braintree_public_key,
        env.braintree_private_key
    )


def team_review(env):
    Team.review_repo = env.team_review_repo
    Team.review_auth = (env.team_review_username, env.team_review_token)


def username_restrictions(website):
    gratipay.RESTRICTED_USERNAMES = os.listdir(website.www_root)


def make_sentry_teller(env):
    if not env.sentry_dsn:
        aspen.log_dammit("Won't log to Sentry (SENTRY_DSN is empty).")
        def noop(*a, **kw):
            pass
        Participant._tell_sentry = noop
        return noop

    sentry = raven.Client(env.sentry_dsn)

    def tell_sentry(exception, state):

        # Decide if we care.
        # ==================

        if isinstance(exception, aspen.Response):

            if exception.code < 500:

                # Only log server errors to Sentry. For responses < 500 we use
                # stream-/line-based access logging. See discussion on:

                # https://github.com/gratipay/gratipay.com/pull/1560.

                return


        # Find a user.
        # ============
        # | is disallowed in usernames, so we can use it here to indicate
        # situations in which we can't get a username.

        user = state.get('user')
        user_id = 'n/a'
        if user is None:
            username = '| no user'
        else:
            is_anon = getattr(user, 'ANON', None)
            if is_anon is None:
                username = '| no ANON'
            elif is_anon:
                username = '| anonymous'
            else:
                participant = getattr(user, 'participant', None)
                if participant is None:
                    username = '| no participant'
                else:
                    username = getattr(user.participant, 'username', None)
                    if username is None:
                        username = '| no username'
                    else:
                        user_id = user.participant.id
                        username = username.encode('utf8')
                        user = { 'id': user_id
                               , 'is_admin': user.participant.is_admin
                               , 'is_suspicious': user.participant.is_suspicious
                               , 'claimed_time': user.participant.claimed_time.isoformat()
                               , 'url': 'https://gratipay.com/{}/'.format(username)
                                }


        # Fire off a Sentry call.
        # =======================

        dispatch_result = state.get('dispatch_result')
        request = state.get('request')
        tags = { 'username': username
               , 'user_id': user_id
                }
        extra = { 'filepath': getattr(dispatch_result, 'match', None)
                , 'request': str(request).splitlines()
                , 'user': user
                 }
        result = sentry.captureException(tags=tags, extra=extra)


        # Emit a reference string to stdout.
        # ==================================

        ident = sentry.get_ident(result)
        aspen.log_dammit('Exception reference: ' + ident)

    Participant._tell_sentry = tell_sentry
    return tell_sentry


class BadEnvironment(SystemExit):
    pass


def accounts_elsewhere(website, env):

    twitter = Twitter(
        env.twitter_consumer_key,
        env.twitter_consumer_secret,
        env.twitter_callback,
    )
    facebook = Facebook(
        env.facebook_app_id,
        env.facebook_app_secret,
        env.facebook_callback,
    )
    github = GitHub(
        env.github_client_id,
        env.github_client_secret,
        env.github_callback,
    )
    google = Google(
        env.google_client_id,
        env.google_client_secret,
        env.google_callback,
    )
    bitbucket = Bitbucket(
        env.bitbucket_consumer_key,
        env.bitbucket_consumer_secret,
        env.bitbucket_callback,
    )
    openstreetmap = OpenStreetMap(
        env.openstreetmap_consumer_key,
        env.openstreetmap_consumer_secret,
        env.openstreetmap_callback,
        env.openstreetmap_api_url,
        env.openstreetmap_auth_url,
    )
    bountysource = Bountysource(
        None,
        env.bountysource_api_secret,
        env.bountysource_callback,
        env.bountysource_api_host,
        env.bountysource_www_host,
    )
    venmo = Venmo(
        env.venmo_client_id,
        env.venmo_client_secret,
        env.venmo_callback,
    )

    signin_platforms = [twitter, github, facebook, google, bitbucket, openstreetmap]
    website.signin_platforms = PlatformRegistry(signin_platforms)
    AccountElsewhere.signin_platforms_names = tuple(p.name for p in signin_platforms)

    # For displaying "Connected Accounts"
    website.social_profiles = [twitter, github, facebook, google, bitbucket, openstreetmap, bountysource]

    all_platforms = signin_platforms + [bountysource, venmo]
    website.platforms = AccountElsewhere.platforms = PlatformRegistry(all_platforms)

    friends_platforms = [p for p in website.platforms if getattr(p, 'api_friends_path', None)]
    website.friends_platforms = PlatformRegistry(friends_platforms)

    for platform in all_platforms:
        platform.icon = website.asset('platforms/%s.16.png' % platform.name)
        platform.logo = website.asset('platforms/%s.png' % platform.name)


def cryptocoin_networks(website):
    website.cryptocoin_networks = [
        {
            'name': 'bitcoin',
            'display_name': 'Bitcoin',
            'logo': website.asset('cryptocoins/bitcoin.png'),
        },
    ]


def find_files(directory, pattern):
    for root, dirs, files in os.walk(directory):
        for filename in fnmatch.filter(files, pattern):
            yield os.path.join(root, filename)


def compile_assets(website):
    client = Client(website.www_root, website.project_root)
    client._website = website
    for spt in find_files(website.www_root+'/assets/', '*.spt'):
        filepath = spt[:-4]                         # /path/to/www/assets/foo.css
        urlpath = spt[spt.rfind('/assets/'):-4]     # /assets/foo.css
        try:
            # Remove any existing compiled asset, so we can access the dynamic
            # one instead (Aspen prefers foo.css over foo.css.spt).
            os.unlink(filepath)
        except:
            pass
        headers = {}
        if website.base_url:
            url = urlparse.urlparse(website.base_url)
            headers[b'HTTP_X_FORWARDED_PROTO'] = str(url.scheme)
            headers[b'HTTP_HOST'] = str(url.netloc)
        content = client.GET(urlpath, **headers).body
        tmpfd, tmpfpath = mkstemp(dir='.')
        os.write(tmpfd, content)
        os.close(tmpfd)
        os.rename(tmpfpath, filepath)
    atexit.register(lambda: clean_assets(website.www_root))


def clean_assets(www_root):
    for spt in find_files(www_root+'/assets/', '*.spt'):
        try:
            os.unlink(spt[:-4])
        except:
            pass


def load_i18n(project_root, tell_sentry):
    # Load the locales
    localeDir = os.path.join(project_root, 'i18n', 'core')
    locales = LOCALES
    for file in os.listdir(localeDir):
        try:
            parts = file.split(".")
            if not (len(parts) == 2 and parts[1] == "po"):
                continue
            lang = parts[0]
            with open(os.path.join(localeDir, file)) as f:
                l = locales[lang.lower()] = Locale(lang)
                c = l.catalog = read_po(f)
                c.plural_func = get_function_from_rule(c.plural_expr)
                try:
                    l.countries = make_sorted_dict(COUNTRIES, l.territories)
                except KeyError:
                    l.countries = COUNTRIES
                try:
                    l.languages_2 = make_sorted_dict(LANGUAGES_2, l.languages)
                except KeyError:
                    l.languages_2 = LANGUAGES_2
        except Exception as e:
            tell_sentry(e, {})

    # Add aliases
    for k, v in list(locales.items()):
        locales.setdefault(ALIASES.get(k, k), v)
        locales.setdefault(ALIASES_R.get(k, k), v)
    for k, v in list(locales.items()):
        locales.setdefault(k.split('_', 1)[0], v)

    # Patch the locales to look less formal
    locales['fr'].currency_formats[None] = parse_pattern('#,##0.00\u202f\xa4')
    locales['fr'].currency_symbols['USD'] = '$'


def other_stuff(website, env):
    website.cache_static = env.gratipay_cache_static
    website.compress_assets = env.gratipay_compress_assets

    if website.cache_static:
        def asset(path):
            fspath = website.www_root+'/assets/'+path
            etag = ''
            try:
                etag = asset_etag(fspath)
            except Exception as e:
                website.tell_sentry(e, {})
            return env.gratipay_asset_url+path+(etag and '?etag='+etag)
        website.asset = asset
        compile_assets(website)
    else:
        website.asset = lambda path: env.gratipay_asset_url+path
        clean_assets(website.www_root)

    website.optimizely_id = env.optimizely_id
    website.include_piwik = env.include_piwik

    website.log_metrics = env.log_metrics


def env():
    env = Environment(
        AWS_SES_ACCESS_KEY_ID           = unicode,
        AWS_SES_SECRET_ACCESS_KEY       = unicode,
        AWS_SES_DEFAULT_REGION          = unicode,
        BASE_URL                        = unicode,
        DATABASE_URL                    = unicode,
        DATABASE_MAXCONN                = int,
        CRYPTO_KEYS                     = unicode,
        GRATIPAY_ASSET_URL              = unicode,
        GRATIPAY_CACHE_STATIC           = is_yesish,
        GRATIPAY_COMPRESS_ASSETS        = is_yesish,
        BALANCED_API_SECRET             = unicode,
        BRAINTREE_SANDBOX_MODE          = is_yesish,
        BRAINTREE_MERCHANT_ID           = unicode,
        BRAINTREE_PUBLIC_KEY            = unicode,
        BRAINTREE_PRIVATE_KEY           = unicode,
        GITHUB_CLIENT_ID                = unicode,
        GITHUB_CLIENT_SECRET            = unicode,
        GITHUB_CALLBACK                 = unicode,
        BITBUCKET_CONSUMER_KEY          = unicode,
        BITBUCKET_CONSUMER_SECRET       = unicode,
        BITBUCKET_CALLBACK              = unicode,
        TWITTER_CONSUMER_KEY            = unicode,
        TWITTER_CONSUMER_SECRET         = unicode,
        TWITTER_CALLBACK                = unicode,
        FACEBOOK_APP_ID                 = unicode,
        FACEBOOK_APP_SECRET             = unicode,
        FACEBOOK_CALLBACK               = unicode,
        GOOGLE_CLIENT_ID                = unicode,
        GOOGLE_CLIENT_SECRET            = unicode,
        GOOGLE_CALLBACK                 = unicode,
        BOUNTYSOURCE_API_SECRET         = unicode,
        BOUNTYSOURCE_CALLBACK           = unicode,
        BOUNTYSOURCE_API_HOST           = unicode,
        BOUNTYSOURCE_WWW_HOST           = unicode,
        VENMO_CLIENT_ID                 = unicode,
        VENMO_CLIENT_SECRET             = unicode,
        VENMO_CALLBACK                  = unicode,
        OPENSTREETMAP_CONSUMER_KEY      = unicode,
        OPENSTREETMAP_CONSUMER_SECRET   = unicode,
        OPENSTREETMAP_CALLBACK          = unicode,
        OPENSTREETMAP_API_URL           = unicode,
        OPENSTREETMAP_AUTH_URL          = unicode,
        UPDATE_CTA_EVERY                = int,
        CHECK_DB_EVERY                  = int,
        DEQUEUE_EMAILS_EVERY            = int,
        OPTIMIZELY_ID                   = unicode,
        SENTRY_DSN                      = unicode,
        LOG_METRICS                     = is_yesish,
        INCLUDE_PIWIK                   = is_yesish,
        TEAM_REVIEW_REPO                = unicode,
        TEAM_REVIEW_USERNAME            = unicode,
        TEAM_REVIEW_TOKEN               = unicode,
        RAISE_SIGNIN_NOTIFICATIONS      = is_yesish,
        RESEND_VERIFICATION_THRESHOLD   = unicode, # anything Postgres can interpret as an interval

        # This is used in our Procfile. (PORT is also used but is provided by
        # Heroku; we don't set it ourselves in our app config.)
        GUNICORN_OPTS                   = unicode,
    )


    # Error Checking
    # ==============

    if env.malformed:
        these = len(env.malformed) != 1 and 'these' or 'this'
        plural = len(env.malformed) != 1 and 's' or ''
        aspen.log_dammit("=" * 42)
        aspen.log_dammit( "Oh no! Gratipay.com couldn't understand %s " % these
                        , "environment variable%s:" % plural
                         )
        aspen.log_dammit(" ")
        for key, err in env.malformed:
            aspen.log_dammit("  {} ({})".format(key, err))
        aspen.log_dammit(" ")
        aspen.log_dammit("See ./default_local.env for hints.")

        aspen.log_dammit("=" * 42)
        keys = ', '.join([key for key in env.malformed])
        raise BadEnvironment("Malformed envvar{}: {}.".format(plural, keys))

    if env.missing:
        these = len(env.missing) != 1 and 'these' or 'this'
        plural = len(env.missing) != 1 and 's' or ''
        aspen.log_dammit("=" * 42)
        aspen.log_dammit( "Oh no! Gratipay.com needs %s missing " % these
                        , "environment variable%s:" % plural
                         )
        aspen.log_dammit(" ")
        for key in env.missing:
            aspen.log_dammit("  " + key)
        aspen.log_dammit(" ")
        aspen.log_dammit( "(Sorry, we must've started looking for "
                        , "%s since you last updated Gratipay!)" % these
                         )
        aspen.log_dammit(" ")
        aspen.log_dammit("Running Gratipay locally? Edit ./local.env.")
        aspen.log_dammit("Running the test suite? Edit ./tests/env.")
        aspen.log_dammit(" ")
        aspen.log_dammit("See ./default_local.env for hints.")

        aspen.log_dammit("=" * 42)
        keys = ', '.join([key for key in env.missing])
        raise BadEnvironment("Missing envvar{}: {}.".format(plural, keys))

    return env


if __name__ == '__main__':
    env()
