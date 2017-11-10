#!/usr/bin/env python
"""link-team-to-package.py team_slug package_name(NPM assumed)
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import sys

from gratipay import wireup
from gratipay.models.team import Team
from gratipay.models.package import Package, NPM

wireup.db(wireup.env())

team = Team.from_slug(sys.argv[1])
package = Package.from_names(NPM, sys.argv[2])

assert team
assert package

package.link_team(team)
print("Team [%s] linked to package [%s] on NPM" % (team.slug, package.name))
