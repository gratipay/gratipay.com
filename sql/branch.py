from gratipay import wireup
from gratipay.billing.payday import Payday

db = wireup.db(wireup.env())

paydays = db.all("SELECT id, nusers, volume, nteams FROM paydays WHERE id > 198")

for rec in paydays:
    payday = Payday()
    payday.id = rec.id
    print("Updating stats for payday #%s" % payday.id)
    payday.update_stats()
