# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from cStringIO import StringIO

import mock
from gratipay.testing import T
from gratipay.testing.email import QueuedEmailHarness
from pytest import raises

from gratipay.project_review_process import ConsolePoster, ProjectReviewProcess
from gratipay.exceptions import NoTeams


class ENV_GH(object):
    project_review_repo = 'some/repo'
    project_review_username = 'cheeseburger'
    project_review_token = 'di3tc0ke'


class ENV(object):
    project_review_repo = ''
    project_review_username = ''
    project_review_token = ''


class Tests(QueuedEmailHarness):

    def setUp(self):
        QueuedEmailHarness.setUp(self)
        self.project_review_process = ProjectReviewProcess(ENV, self.db, self.app.email_queue)


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


    @mock.patch('gratipay.project_review_process.requests.post')
    def test_github_poster_attempts_to_post_to_github(self, post):
        foo = self.make_team(name='foo')
        bar = self.make_team(name='bar')
        baz = self.make_team(name='baz')

        post.return_value = ''

        ProjectReviewProcess(ENV_GH, self.db, self.app.email_queue).start(foo, bar, baz)

        assert post.call_count == 1
        args, kwargs = post.mock_calls[0][1:]
        assert args[0] == 'https://api.github.com/repos/some/repo/issues'
        assert kwargs['data'] == (
            '{"body": "*This application will remain open for at least a week.*\\n\\n'
            '## Projects\\n\\nhttps://gratipay.com/foo/\\nhttps://gratipay.com/bar/\\n'
            'https://gratipay.com/baz/\\n\\n'
            '## Badge\\n\\n'
            'Add a [badge](http://shields.io/) to your README?\\n\\n'
            '[![Gratipay](https://img.shields.io/gratipay/project/foo.svg)](https://gratipay.com/foo/)\\n\\n'
            '```markdown\\n'
            '[![Gratipay](https://img.shields.io/gratipay/project/foo.svg)](https://gratipay.com/foo/)\\n'
            '```", "title": "foo and 2 other projects"}')
        assert kwargs['auth'] == ('cheeseburger', 'di3tc0ke')


    def test_team_objects_get_review_url(self):
        foo = self.make_team(name='foo')
        assert foo.review_url is None
        self.project_review_process.start(foo)
        assert foo.review_url == T('foo').review_url == 'some-github-issue'


    def test_owner_gets_an_email_notification(self):
        foo = self.make_team(name='foo')
        self.project_review_process.start(foo)
        assert self.get_last_email()['subject'] == 'We have your application!'


    def test_no_teams_raises(self):
        raises(NoTeams, self.project_review_process.start)


    def test_multiple_owners_raises(self):
        foo = self.make_team(name='foo')
        bar = self.make_team(name='bar', owner='crusher')
        raises(AssertionError, self.project_review_process.start, foo, bar)
