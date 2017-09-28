# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import json
import pprint
import requests
import sys

from aspen import log

from gratipay.exceptions import NoTeams
from gratipay.models.participant import Participant


SHIELD = "[![Gratipay](https://img.shields.io/gratipay/project/{}.svg)](https://gratipay.com{})"


class ProjectReviewProcess(object):

    def __init__(self, env, db, email_queue):
        repo = env.project_review_repo
        auth = (env.project_review_username, env.project_review_token)
        self.db = db
        self.email_queue = email_queue
        self._poster = GitHubPoster(repo, auth) if repo else ConsolePoster()


    def start(self, *teams):
        """Given team objects, kick off a review process by:

        1. creating an issue in our project review repo on GitHub, and
        2. sending an email notification to the owner of the team(s).

        It's a bug to pass in teams that don't all have the same owner.

        :return: the URL of the new review issue

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

        body = [ '*This application will remain open for at least a week.*'
               , ''
               , '## Project' + ('s' if nteams > 1 else '')
               , ''
                ]
        team_ids = []
        owner_usernames = set()
        for team in teams:
            team_ids.append(team.id)
            owner_usernames.add(team.owner)
            body.append('https://gratipay.com{}'.format(team.url_path))
        assert len(owner_usernames) == 1, owner_usernames

        shield = SHIELD.format(teams[0].slug, teams[0].url_path)
                               # let them discover how to adapt for additional projects
        body += [ ''
                , '## Badge'
                , ''
                , 'Add a [badge](http://shields.io/) to your README?'
                , ''
                , shield
                , ''
                , '```markdown'
                , shield
                , '```'
                 ]

        data = json.dumps({'title': title, 'body': '\n'.join(body)})
        review_url = self._poster.post(data)

        self.db.run("UPDATE teams SET review_url=%s WHERE id = ANY(%s)", (review_url, team_ids))
        [team.set_attributes(review_url=review_url) for team in teams]

        owner = Participant.from_username(owner_usernames.pop())
        self.email_queue.put( owner
                            , 'project-review'
                            , review_url=team.review_url
                            , include_unsubscribe=False
                            , _user_initiated=False
                             )

        return review_url


class GitHubPoster(object):
    """Sends data to GitHub.
    """

    def __init__(self, repo, auth):
        self.repo = repo
        self.api_url = "https://api.github.com/repos/{}/issues".format(repo)
        self.auth = auth

    def post(self, data):
        """POST data to GitHub and return the issue URL.
        """
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
        """POST data to nowhere and return a URL of lies.
        """
        p = lambda *a, **kw: print(*a, file=self.fp)
        p('-'*78,)
        p(pprint.pformat(json.loads(data)))
        p('-'*78)
        return 'some-github-issue'
