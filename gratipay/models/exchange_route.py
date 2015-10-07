from __future__ import absolute_import, division, print_function, unicode_literals

import braintree
from postgres.orm import Model


class ExchangeRoute(Model):

    typname = "exchange_routes"

    def __bool__(self):
        return self.error != 'invalidated'

    __nonzero__ = __bool__

    @classmethod
    def from_id(cls, id):
        r = cls.db.one("""
            SELECT r.*::exchange_routes
              FROM exchange_routes r
             WHERE id = %(id)s
        """, locals())
        if r:
            from gratipay.models.participant import Participant  # XXX Red hot hack!
            r.set_attributes(participant=Participant.from_id(r.participant))
        return r

    @classmethod
    def from_network(cls, participant, network):
        participant_id = participant.id
        r = cls.db.one("""
            SELECT r.*::exchange_routes
              FROM current_exchange_routes r
             WHERE participant = %(participant_id)s
               AND network = %(network)s
        """, locals())
        if r:
            r.set_attributes(participant=participant)
        return r

    @classmethod
    def from_address(cls, participant, network, address):
        participant_id = participant.id
        r = cls.db.one("""
            SELECT r.*::exchange_routes
              FROM exchange_routes r
             WHERE participant = %(participant_id)s
               AND network = %(network)s
               AND address = %(address)s
        """, locals())
        if r:
            r.set_attributes(participant=participant)
        return r

    @classmethod
    def insert(cls, participant, network, address, error='', fee_cap=None, cursor=None):
        participant_id = participant.id
        r = (cursor or cls.db).one("""
            INSERT INTO exchange_routes
                        (participant, network, address, error, fee_cap)
                 VALUES (%(participant_id)s, %(network)s, %(address)s, %(error)s, %(fee_cap)s)
              RETURNING exchange_routes.*::exchange_routes
        """, locals())
        if network == 'braintree-cc':
            participant.update_giving_and_teams()
        r.set_attributes(participant=participant)
        return r

    def invalidate(self):
        if self.network == 'braintree-cc':
            braintree.PaymentMethod.delete(self.address)

        # For Paypal, we remove the record entirely to prevent
        # an integrity error if the user tries to add the route again
        if self.network == 'paypal':
            # XXX This doesn't sound right. Doesn't this corrupt history pages?
            self.db.run("DELETE FROM exchange_routes WHERE id=%s", (self.id,))
        else:
            self.update_error('invalidated')

    def update_error(self, new_error):
        id = self.id
        old_error = self.error
        if old_error == 'invalidated':
            return
        self.db.run("""
            UPDATE exchange_routes
               SET error = %(new_error)s
             WHERE id = %(id)s
        """, locals())
        self.set_attributes(error=new_error)

        # Update cached amounts if requested and necessary
        if self.network != 'braintree-cc':
            return
        if self.participant.is_suspicious or bool(new_error) == bool(old_error):
            return


        # XXX *White* hot hack!
        # =====================
        # During payday, participant is a record from a select of
        # payday_participants (or whatever), *not* an actual Participant
        # object. We need the real deal so we can use a method on it ...

        from gratipay.models.participant import Participant
        participant = Participant.from_username(self.participant.username)
        participant.update_giving_and_teams()
