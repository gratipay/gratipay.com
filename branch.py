import os

import gittip
from gittip import wireup

gittip.RESTRICTED_USERNAMES = set(os.listdir('www'))

db = wireup.db(wireup.env())
deactivated = db.all("select participants.*::participants from participants "
                     "where username like 'deactivated-%'")

for p in deactivated:
    print(p.username)
    if not p.claimed_time:
        p.set_as_claimed()
    p.change_username(p.username[len('deactivated-'):])
    p.close(disbursement_strategy=None)
