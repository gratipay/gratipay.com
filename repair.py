#!/usr/bin/env python
from gittip import wireup

db = wireup.db(wireup.env())


affected = db.all("""

    select p.username, p.balance, count(*), sum(t.amount), array_agg(t.id) as tips from (
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

def transfer(tipper, tippee, amount):
    db.run("""

        UPDATE participants SET balance = (balance - %(amount)s) WHERE username = %(tipper)s;
        UPDATE participants SET balance = (balance + %(amount)s) WHERE username = %(tippee)s;
        INSERT INTO transfers (tipper, tippee, amount, context)
             VALUES ( ( SELECT p.username
                          FROM participants p
                          JOIN participants p2 ON p.id = p2.id
                         WHERE p2.username = %(tipper)s)
                    , ( SELECT p.username
                          FROM participants p
                          JOIN participants p2 ON p.id = p2.id
                         WHERE p2.username = %(tippee)s)
                    , %(amount)s
                    , 'one-off'
                    );

    """)

for user in affected:
    for tip in user.tips:
        transfer(tip.tipper, tip.tippee, tip.amount)
