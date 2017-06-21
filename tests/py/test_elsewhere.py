from __future__ import absolute_import, division, print_function, unicode_literals

import json
from base64 import b64encode

import mock

from gratipay.elsewhere import UserInfo
from gratipay.models.account_elsewhere import AccountElsewhere
from gratipay.testing import Harness, P
import gratipay.testing.elsewhere as user_info_examples


class TestElsewhere(Harness):

    def test_associate_csrf(self):
        response = self.client.GxT('/on/github/associate?state=49b7c66246c7')
        assert response.code == 400

    def test_associate_with_empty_cookie_raises_400(self):
        self.client.cookie[b'github_deadbeef'] = b''
        response = self.client.GxT('/on/github/associate?state=deadbeef')
        assert response.code == 400

    def test_extract_user_info(self):
        for platform in self.platforms:
            user_info = getattr(user_info_examples, platform.name)()
            r = platform.extract_user_info(user_info)
            assert isinstance(r, UserInfo)
            assert r.user_id is not None
            assert len(r.user_id) > 0

    @mock.patch('gratipay.elsewhere.Platform.api_get')
    def test_get_user_info_quotes_values_in_query_string(self, api_get):
        self.platforms.twitter.get_user_info('user_name', "'")
        api_get.assert_called_with("/users/show.json?screen_name=%27", sess=None)

    @mock.patch('gratipay.elsewhere.bitbucket.Bitbucket.api_get')
    def test_get_user_info_does_not_quotes_values_in_url(self, api_get):
        self.platforms.bitbucket.get_user_info('user_name', "'")
        api_get.assert_called_with("/2.0/users/'", sess=None)

    def test_opt_in_can_change_username(self):
        account = self.make_elsewhere('twitter', 1, 'alice')
        expected = 'bob'
        actual = account.opt_in('bob')[0].participant.username
        assert actual == expected

    def test_opt_in_doesnt_have_to_change_username(self):
        self.make_participant('bob')
        account = self.make_elsewhere('twitter', 1, 'alice')
        expected = account.participant.username # A random one.
        actual = account.opt_in('bob')[0].participant.username
        assert actual == expected

    def test_opt_in_resets_is_closed_to_false(self):
        alice = self.make_elsewhere('twitter', 1, 'alice')
        alice.participant.update_is_closed(True)
        user = alice.opt_in('alice')[0]
        assert not user.participant.is_closed
        assert not P('alice').is_closed

    @mock.patch('requests_oauthlib.OAuth2Session.fetch_token')
    @mock.patch('gratipay.elsewhere.Platform.get_user_self_info')
    @mock.patch('gratipay.elsewhere.Platform.get_user_info')
    def test_connect_might_need_confirmation(self, gui, gusi, ft):
        self.make_participant('alice', claimed_time='now')
        self.make_participant('bob', claimed_time='now')

        gusi.return_value = self.client.website.platforms.github.extract_user_info({'id': 2})
        gui.return_value = self.client.website.platforms.github.extract_user_info({'id': 1})
        ft.return_value = None

        cookie = b64encode(json.dumps(['query_data', 'connect', '', '2']))
        response = self.client.GxT('/on/github/associate?state=deadbeef',
                                   auth_as='alice',
                                   cookies={b'github_deadbeef': cookie})
        assert response.code == 302
        assert response.headers['Location'].startswith('/on/confirm.html?id=')

    def test_redirect_csrf(self):
        response = self.client.GxT('/on/github/redirect')
        assert response.code == 405

    def test_redirects(self, *classes):
        self.make_participant('alice')
        data = dict(action='opt-in', then='/', user_id='')
        for platform in self.platforms:
            platform.get_auth_url = lambda *a, **kw: ('', '', '')
            response = self.client.PxST('/on/%s/redirect' % platform.name,
                                        data, auth_as='alice')
            assert response.code == 302

    def test_upsert(self):
        for platform in self.platforms:
            user_info = getattr(user_info_examples, platform.name)()
            account = AccountElsewhere.upsert(platform.extract_user_info(user_info))
            assert isinstance(account, AccountElsewhere)

    @mock.patch('gratipay.elsewhere.Platform.get_user_info')
    def test_user_pages(self, get_user_info):
        for platform in self.platforms:
            alice = UserInfo( platform=platform.name
                            , user_id='0'
                            , user_name='alice'
                            , is_team=False
                             )
            get_user_info.side_effect = lambda *a: alice
            response = self.client.GET('/on/%s/alice/' % platform.name)
            assert response.code == 200
            assert 'has not joined' in response.body.decode('utf8')

    def test_user_pages_are_404_for_unknown_elsewhere_user(self):
        for platform in self.platforms:
            if not hasattr(platform, 'api_user_name_info_path'):
                continue
            r = self.client.GxT("/on/%s/%s/" % (platform.name, 'ijroioifeef'))
            assert "Account not found on %s." % (platform.display_name) in r.body
            assert r.code == 404

    def test_user_pages_are_400_for_invalid_characters(self):
        platform = self.platforms.twitter
        for username in ('AA%09BB', 'AA%0DBB', 'AA%0ABB'):
            r = self.client.GxT('/on/{}/{}/'.format(platform.name, username))
            assert "Invalid character in elsewhere account username." in r.body
            assert r.code == 400

    def test_failure_page_accepts_valid_username(self):
        self.client.GET('/on/twitter/Gratipay/')  # normal case will have the db primed
        response = self.client.GET('/on/twitter/Gratipay/failure.html')
        assert response.code == 200


class TestConfirmTakeOver(Harness):

    def setUp(self):
        Harness.setUp(self)
        self.alice_elsewhere = self.make_elsewhere('twitter', -1, 'alice')
        token, expires = self.alice_elsewhere.make_connect_token()
        self.connect_cookie = {b'connect_%s' % self.alice_elsewhere.id: token}
        self.bob = self.make_participant('bob', claimed_time='now')

    def test_confirm(self):
        url = '/on/confirm.html?id=%s' % self.alice_elsewhere.id

        response = self.client.GxT(url)
        assert response.code == 403

        response = self.client.GxT(url, auth_as='bob')
        assert response.code == 400
        assert 'bad connect token' in response.body

        response = self.client.GET(url, auth_as='bob', cookies=self.connect_cookie)
        assert response.code == 200
        assert 'Please Confirm' in response.body

    def test_confirm_gives_400_for_garbage(self):
        assert self.client.GxT('/on/confirm.html?id=garbage', auth_as='bob').code == 400

    def test_take_over(self):
        data = {'account_id': self.alice_elsewhere.id, 'should_transfer': 'yes'}

        response = self.client.PxST('/on/take-over.html', data=data)
        assert response.code == 403

        response = self.client.PxST('/on/take-over.html', data=data, auth_as='bob')
        assert response.code == 400
        assert 'bad connect token' in response.body

        response = self.client.PxST('/on/take-over.html', data=data, auth_as='bob',
                                    cookies=self.connect_cookie)
        assert response.code == 302
        assert response.headers['Location'] == '/bob/'


class TestFriendFinder(Harness):

    def test_twitter_get_friends_for(self):
        platform = self.platforms.twitter
        user_info = platform.extract_user_info(user_info_examples.twitter())
        account = AccountElsewhere.upsert(user_info)
        friends, nfriends, pages_urls = platform.get_friends_for(account)
        assert nfriends > 0

    def test_github_get_friends_for(self):
        platform = self.platforms.github
        user_info = platform.extract_user_info(user_info_examples.github())
        account = AccountElsewhere.upsert(user_info)
        friends, nfriends, pages_urls = platform.get_friends_for(account)
        assert nfriends > 0
