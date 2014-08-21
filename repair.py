#!/usr/bin/env python
from __future__ import print_function

from gittip import wireup

db = wireup.db(wireup.env())


affected = db.all("""

    select p.username, p.balance, count(*), sum(t.amount), json_agg(t.*) as tips from (
      select distinct on (tipper, tippee) t.* from tips t
          where mtime < (select ts_start from paydays where ts_start::date = '2014-08-14')
          order by tipper, tippee, mtime desc
    ) as t
      join participants p  on p.username  = t.tipper
      join participants p2 on p2.username = t.tippee
      where p2.claimed_time  is not null
        and p.is_suspicious  is not true
        and p2.is_suspicious is not true
        and p.balance > 0
        and t.amount > 0
        and (
          select id from transfers
            where timestamp::date = '2014-08-14' and context = 'tip'
              and tipper = t.tipper and tippee = t.tippee
        ) is null

      group by p.username, p.balance
      having sum(t.amount) <= p.balance or p.number = 'plural' and p.last_bill_result = '';

""")

def transfer(tip):
    db.run("""

        UPDATE participants SET balance = (balance - %(amount)s) WHERE username = %(tipper)s;
        UPDATE participants SET balance = (balance + %(amount)s) WHERE username = %(tippee)s;
        INSERT INTO transfers (tipper, tippee, amount, context)
             VALUES (%(tipper)s, %(tippee)s, %(amount)s, 'one-off');

    """, tip)

for user in affected:
    print(user.username)
    for tip in user.tips:
        print('   ', tip['amount'], 'to', tip['tippee'])
        transfer(tip)

print('\nnew balances:')
for user in affected:
    b = db.one("select balance from participants where username = %s", (user.username,))
    print('   ', b, user.username)
