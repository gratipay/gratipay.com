# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from cStringIO import StringIO

import mock
from gratipay.testing import Harness
from pytest import raises

from gratipay.project_review_repo import ConsolePoster, ProjectReviewRepo
from gratipay.exceptions import NoTeams


class Tests(Harness):

    def test_console_poster_posts_to_fp(self):
        fp = StringIO()
        poster = ConsolePoster(fp)
        poster.post('{"blah": "blah blah"}')
        fp.seek(0)
        assert fp.read() == '''\
------------------------------------------------------------------------------
{u'blah': u'blah blah'}
------------------------------------------------------------------------------
'''


    @mock.patch('gratipay.project_review_repo.requests.post')
    def test_github_poster_attempts_to_post_to_github(self, post):
        post.return_value = ''

        class HackEnv:
            project_review_repo = 'some/repo'
            project_review_username = 'cheeseburger'
            project_review_token = 'di3tc0ke'
        env = HackEnv()

        class HackTeam:
            def __init__(self, name):
                self.name = name
                self.url_path = '/'+name

        repo = ProjectReviewRepo(env)
        repo.create_issue(*map(HackTeam, ['foo', 'bar', 'baz']))

        assert post.call_count == 1
        args, kwargs = post.mock_calls[0][1:]
        assert args[0] == 'https://api.github.com/repos/some/repo/issues'
        assert kwargs['data'] == (
            '{"body": "https://gratipay.com/foo\\nhttps://gratipay.com/bar\\n'
            'https://gratipay.com/baz\\n\\n(This application will remain open '
            'for at least a week.)", "title": "foo and 2 other projects"}')
        assert kwargs['auth'] == ('cheeseburger', 'di3tc0ke')


    def test_no_teams_raises(self):
        class Env: __getattr__ = lambda *a: ''
        raises(NoTeams, ProjectReviewRepo(Env()).create_issue)
