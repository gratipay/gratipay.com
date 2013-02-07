import datetime
import gittip
import requests
from aspen import json, log, Response
from aspen.utils import to_age, utc, typecheck
from gittip.elsewhere import AccountElsewhere, _resolve


class DevNetAccount(AccountElsewhere):
    platform = u'devnet'


def resolve(screen_name):
    return _resolve(u'devnet', u'screen_name', screen_name)


def oauth_url(website, action, then=""):
    """Return a URL to start oauth dancing with DevNet.

    For GitHub we can pass action and then through a querystring. For Twitter
    we can't, so we send people through a local URL first where we stash this
    info in an in-memory cache (eep! needs refactoring to scale).

    Not sure why website is here. Vestige from GitHub forebear?

    """
    return "/on/devnet/login.html?action=%s&then=%s" % (action, then)


def get_user_info(screen_name):
    """Given a unicode, return a dict.
    """
    typecheck(screen_name, unicode)
    rec = gittip.db.fetchone( "SELECT user_info FROM elsewhere "
                              "WHERE platform='devnet' "
                              "AND user_info->'screen_name' = %s"
                            , (screen_name,)
                             )
    if rec is not None:
        user_info = rec['user_info']
    else:
        user_info = {"screen_name": screen_name}

    return user_info
