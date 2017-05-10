from __future__ import absolute_import, division, print_function, unicode_literals

import braintree
from postgres.orm import Model


class ExchangeRoute(Model):

    typname = "exchange_routes"

    def __eq__(self, other):
        if not isinstance(other, ExchangeRoute):
            return False
        return self.id == other.id

    def __ne__(self, other):
        if not isinstance(other, ExchangeRoute):
            return True
        return self.id != other.id

    def __repr__(self):
        return '<ExchangeRoute: %s on %s>' % (repr(self.address), repr(self.network))


    # Constructors
    # ============

    @classmethod
    def from_id(cls, id, cursor=None):
        route = (cursor or cls.db).one("""
            SELECT r.*::exchange_routes
              FROM exchange_routes r
             WHERE id = %(id)s
        """, locals())
        if route:
            from gratipay.models.participant import Participant  # XXX Red hot hack!
            route.set_attributes(participant=Participant.from_id(route.participant))
        return route

    @classmethod
    def from_network(cls, participant, network, cursor=None):
        participant_id = participant.id
        route = (cursor or cls.db).one("""
            SELECT r.*::exchange_routes
              FROM current_exchange_routes r
             WHERE participant = %(participant_id)s
               AND network = %(network)s
        """, locals())
        if route:
            route.set_attributes(participant=participant)
        return route

    @classmethod
    def from_address(cls, participant, network, address, cursor=None):
        participant_id = participant.id
        route = (cursor or cls.db).one("""
            SELECT r.*::exchange_routes
              FROM exchange_routes r
             WHERE participant = %(participant_id)s
               AND network = %(network)s
               AND address = %(address)s
        """, locals())
        if route:
            route.set_attributes(participant=participant)
        return route

    @classmethod
    def insert(cls, participant, network, address, fee_cap=None, cursor=None):
        participant_id = participant.id
        error = ''
        route = (cursor or cls.db).one("""
            INSERT INTO exchange_routes
                        (participant, network, address, error, fee_cap)
                 VALUES (%(participant_id)s, %(network)s, %(address)s, %(error)s, %(fee_cap)s)
              RETURNING exchange_routes.*::exchange_routes
        """, locals())
        if network == 'braintree-cc':
            participant.update_giving_and_teams()
        route.set_attributes(participant=participant)
        return route

    def invalidate(self):
        if self.network == 'braintree-cc':
            braintree.PaymentMethod.delete(self.address)
        with self.db.get_cursor() as cursor:
            self.db.run("UPDATE exchange_routes SET is_deleted=true WHERE id=%s", (self.id,))
            payload = dict( id=self.participant.id
                          , exchange_route=self.id
                          , action='invalidate route'
                          , address=self.address
                           )
            self.app.add_event(cursor, 'participant', payload)
        self.set_attributes(is_deleted=True)

    def revive(self):
        assert self.network == 'paypal'  # sanity check
        with self.db.get_cursor() as cursor:
            cursor.run("UPDATE exchange_routes SET is_deleted=false WHERE id=%s", (self.id,))
            payload = dict( id=self.participant.id
                          , exchange_route=self.id
                          , action='revive route'
                          , address=self.address
                           )
            self.app.add_event(cursor, 'participant', payload)
        self.set_attributes(is_deleted=False)

    def update_error(self, new_error):
        if self.is_deleted:
            return

        id = self.id
        old_error = self.error

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
