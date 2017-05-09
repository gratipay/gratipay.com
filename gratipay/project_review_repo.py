# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import json
import pprint
import requests
import sys

from aspen import log

from gratipay.exceptions import NoTeams


class ProjectReviewRepo(object):

    def __init__(self, env):
        repo = env.project_review_repo
        auth = (env.project_review_username, env.project_review_token)
        self._poster = GitHubPoster(repo, auth) if repo else ConsolePoster()


    def create_issue(self, *teams):
        """Given team objects, POST to GitHub, and return the URL of the new issue.
        """
        if not teams:
            raise NoTeams()
        nteams = len(teams)
        if nteams == 1:
            title = teams[0].name
        elif nteams == 2:
            title = "{} and {}".format(*[t.name for t in teams])
        else:
            title = "{} and {} other projects".format(teams[0].name, nteams-1)
        body = []
        for team in teams:
            body.append('https://gratipay.com{}'.format(team.url_path))
        body.extend(['', '(This application will remain open for at least a week.)'])
        data = json.dumps({'title': title, 'body': '\n'.join(body)})
        return self._poster.post(data)


class GitHubPoster(object):
    """Sends data to GitHub.
    """

    def __init__(self, repo, auth):
        self.repo = repo
        self.api_url = "https://api.github.com/repos/{}/issues".format(repo)
        self.auth = auth

    def post(self, data):
        out = ''
        try:
            r = requests.post(self.api_url, auth=self.auth, data=data)
            if r.status_code == 201:
                out = r.json()['html_url']
            else:
                log(r.status_code)
                log(r.text)
            err = str(r.status_code)
        except:
            err = "eep"
        if not out:
            out = "https://github.com/{}/issues#error-{}".format(self.repo, err)
        return out


class ConsolePoster(object):
    """Dumps data to stdout.
    """

    def __init__(self, fp=sys.stdout):
        self.fp = fp

    def post(self, data):
        p = lambda *a, **kw: print(*a, file=self.fp)
        p('-'*78,)
        p(pprint.pformat(json.loads(data)))
        p('-'*78)
        return 'some-github-issue'
