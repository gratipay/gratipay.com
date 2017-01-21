from __future__ import absolute_import, division, print_function, unicode_literals

from aspen import Response
from gratipay.elsewhere import PlatformOAuth2
from gratipay.elsewhere._extractors import any_key, key, not_available
from gratipay.elsewhere._paginators import keys_paginator


class Bitbucket(PlatformOAuth2):

    # Platform attributes
    name = 'bitbucket'
    display_name = 'Bitbucket'
    account_url = 'https://bitbucket.org/{user_name}'

    # Auth attributes
    auth_url = 'https://bitbucket.org/site/oauth2/authorize'
    access_token_url = 'https://bitbucket.org/site/oauth2/access_token'
    oauth_default_scope = ['account']

    # API attributes
    api_format = 'json'
    api_paginator = keys_paginator('values', prev='previous', total='size')
    api_url = 'https://bitbucket.org/api'
    api_user_info_path = '/2.0/users/{user_id}'
    api_user_name_info_path = '/2.0/users/{user_name}'
    api_user_self_info_path = '/2.0/user'
    api_team_members_path = '/2.0/teams/{user_name}/members'
    api_friends_path = '/2.0/users/{user_name}/following'

    # User info extractors
    x_user_info = key('user')
    x_user_id = key('uuid')
    x_user_name = key('username')
    x_display_name = key('display_name')
    x_email = not_available
    x_avatar_url = any_key('avatar', ('links', 'avatar', 'href'))
    x_is_team = key('type', lambda v: v == 'team')
