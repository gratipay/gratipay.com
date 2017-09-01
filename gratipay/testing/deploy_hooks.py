# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import os
import subprocess
import sys

from gratipay.testing import Harness


class DeployHooksHarness(Harness):

    def run_deploy_hooks(self, _deploy_dir=None):
        project_root = self.app.website.project_root
        if _deploy_dir is None:
            _deploy_dir = os.path.join(project_root, 'deploy')

        path = lambda hook: os.path.join(_deploy_dir, hook)
        load = lambda hook: open(path(hook)).read()

        # Suppress asset cleaning to avoid disturbing shared state.
        env = os.environ.copy()
        env['__HACK_SUPPRESS_ASSET_CLEANING'] = 'yes'

        self.db.run(load('before.sql'))
        subprocess.check_call([sys.executable, path('after.py')], env=env)
        self.db.run(load('after.sql'))
