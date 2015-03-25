import balanced

from gratipay import wireup

env = wireup.env()
db = wireup.db(env)
wireup.billing(env)

with db.get_cursor() as cursor:
    def update_balanced_href(id, href):
        cursor.run("""
            UPDATE participants
               SET balanced_customer_href=%s
             WHERE id=%s
        """, (href, id))

    participants = cursor.all("""
        SELECT id, balanced_customer_href
          FROM participants
         WHERE balanced_customer_href NOT LIKE '/customers/%';
    """)

    total = len(participants)
    counter = 0

    for p in participants:
        counter += 1
        if counter % 10 == 1:
            print "processing participant %i/%i" % (counter, total)
        customer = balanced.Customer.fetch(p.balanced_customer_href)
        update_balanced_href(p.id, customer.href)
