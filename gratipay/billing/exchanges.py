"""Functions for moving money between Gratipay and the outside world.
"""
from __future__ import unicode_literals

from decimal import Decimal, ROUND_UP

import balanced
import braintree

from aspen import log
from aspen.utils import typecheck
from gratipay.exceptions import NegativeBalance, NotWhitelisted
from gratipay.models.exchange_route import ExchangeRoute


BALANCED_CLASSES = {
    "bank_accounts": balanced.BankAccount,
    "cards": balanced.Card,
}

BALANCED_LINKS = {
    "bank_accounts": {
        "bank_accounts.bank_account_verification": "/verifications/{bank_accounts.bank_account_verification}",
        "bank_accounts.bank_account_verifications": "/bank_accounts/{bank_accounts.id}/verifications",
        "bank_accounts.credits": "/bank_accounts/{bank_accounts.id}/credits",
        "bank_accounts.customer": "/customers/{bank_accounts.customer}",
        "bank_accounts.debits": "/bank_accounts/{bank_accounts.id}/debits",
        "bank_accounts.settlements": "/bank_accounts/{bank_accounts.id}/settlements"
    },
    "cards": {
        "cards.card_holds": "/cards/{cards.id}/card_holds",
        "cards.customer": "/customers/{cards.customer}",
        "cards.debits": "/cards/{cards.id}/debits",
        "cards.disputes": "/cards/{cards.id}/disputes"
    }
}

def thing_from_href(things, href):
    """This is a temporary hack, we'll get rid of it when we migrate to Stripe.
    """
    id = href.rsplit('/', 1)[1]
    d = {'href': href, 'id': id, 'links': {}, 'meta': {}}
    C = BALANCED_CLASSES[things]
    return C(**{things: [d], 'links': BALANCED_LINKS[things]})


# Balanced has a $0.50 minimum. We go even higher to avoid onerous
# per-transaction fees. See:
# https://github.com/gratipay/gratipay.com/issues/167

MINIMUM_CHARGE = Decimal("9.41")
MINIMUM_CREDIT = Decimal("10.00")

FEE_CHARGE = ( Decimal("0.30")   # $0.30
             , Decimal("0.029")  #  2.9%
              )
FEE_CREDIT = Decimal("0.00")    # Balanced doesn't actually charge us for this,
                                # because we were in the door early enough.


def upcharge(amount):
    """Given an amount, return a higher amount and the difference.
    """
    typecheck(amount, Decimal)
    charge_amount = (amount + FEE_CHARGE[0]) / (1 - FEE_CHARGE[1])
    charge_amount = charge_amount.quantize(FEE_CHARGE[0], rounding=ROUND_UP)
    return charge_amount, charge_amount - amount

assert upcharge(MINIMUM_CHARGE) == (Decimal('10.00'), Decimal('0.59'))


def skim_credit(amount):
    """Given an amount, return a lower amount and the difference.
    """
    typecheck(amount, Decimal)
    return amount - FEE_CREDIT, FEE_CREDIT


def repr_exception(e):
    if isinstance(e, balanced.exc.HTTPError):
        return '%s %s, %s' % (e.status_code, e.status, e.description)
    else:
        return repr(e)


def create_card_hold(db, participant, amount):
    """Create a hold on the participant's credit card.

    Amount should be the nominal amount. We'll compute Gratipay's fee below
    this function and add it to amount to end up with charge_amount.

    """
    typecheck(amount, Decimal)

    username = participant.username


    # Perform some last-minute checks.
    # ================================

    if participant.is_suspicious is not False:
        raise NotWhitelisted      # Participant not trusted.

    route = ExchangeRoute.from_network(participant, 'braintree-cc')
    if not route:
        return None, 'No credit card'


    # Go to Braintree.
    # ================

    cents, amount_str, charge_amount, fee = _prep_hit(amount)
    amount = charge_amount - fee
    msg = "Holding " + amount_str + " on Braintree for " + username + " ... "

    hold = None
    error = ""
    try:
        result = braintree.Transaction.sale({
            'amount': str(cents/100.0),
            'customer_id': route.participant.braintree_customer_id,
            'payment_method_token': route.address,
            'options': { 'submit_for_settlement': False },
            'custom_fields': {'participant_id': participant.id}
        })

        if result.is_success and result.transaction.status == 'authorized':
            log(msg + "succeeded.")
            error = ""
            hold = result.transaction
        elif result.is_success:
            error = "Transaction status was %s" % result.transaction.status
        else:
            error = result.message

        if error == '':
            log(msg + "succeeded.")
        else:
            log(msg + "failed: %s" % error)
            record_exchange(db, route, amount, fee, participant, 'failed', error)

    except Exception as e:
        error = repr_exception(e)
        log(msg + "failed: %s" % error)
        record_exchange(db, route, amount, fee, participant, 'failed', error)

    return hold, error


def capture_card_hold(db, participant, amount, hold):
    """Capture the previously created hold on the participant's credit card.
    """
    typecheck( hold, braintree.Transaction
             , amount, Decimal
              )

    username = participant.username
    assert participant.id == int(hold.custom_fields['participant_id'])

    route = ExchangeRoute.from_address(participant, 'braintree-cc', hold.credit_card['token'])
    assert isinstance(route, ExchangeRoute)

    cents, amount_str, charge_amount, fee = _prep_hit(amount)
    amount = charge_amount - fee  # account for possible rounding
    e_id = record_exchange(db, route, amount, fee, participant, 'pre')

    # TODO: Find a way to link transactions and corresponding exchanges
    # meta = dict(participant_id=participant.id, exchange_id=e_id)

    error = ''
    try:
        result = braintree.Transaction.submit_for_settlement(hold.id, str(cents/100.00))
        assert result.is_success
        if result.transaction.status != 'submitted_for_settlement':
            error = result.transaction.status
    except Exception as e:
        error = repr_exception(e)

    if error == '':
        record_exchange_result(db, e_id, 'succeeded', None, participant)
        log("Captured " + amount_str + " on Braintree for " + username)
    else:
        record_exchange_result(db, e_id, 'failed', error, participant)
        raise Exception(error)


def cancel_card_hold(hold):
    """Cancel the previously created hold on the participant's credit card.
    """
    result = braintree.Transaction.void(hold.id)
    assert result.is_success

    amount = hold.amount
    participant_id = hold.custom_fields['participant_id']
    log("Canceled a ${:.2f} hold for {}.".format(amount, participant_id))


def _prep_hit(unrounded):
    """Takes an amount in dollars. Returns cents, etc.

    cents       This is passed to the payment processor charge API. This is
                the value that is actually charged to the participant. It's
                an int.
    amount_str  A detailed string representation of the amount.
    upcharged   Decimal dollar equivalent to `cents'.
    fee         Decimal dollar amount of the fee portion of `upcharged'.

    The latter two end up in the db in a couple places via record_exchange.

    """
    also_log = ''
    rounded = unrounded
    if unrounded < MINIMUM_CHARGE:
        rounded = MINIMUM_CHARGE  # per github/#167
        also_log = ' [rounded up from $%s]' % unrounded

    upcharged, fee = upcharge(rounded)
    cents = int(upcharged * 100)

    amount_str = "%d cents ($%s%s + $%s fee = $%s)"
    amount_str %= cents, rounded, also_log, fee, upcharged

    return cents, amount_str, upcharged, fee


def get_ready_payout_routes_by_network(db, network):
    hack = db.all("""
        SELECT p.*::participants, r.*::exchange_routes
          FROM participants p
          JOIN current_exchange_routes r ON p.id = r.participant
         WHERE p.balance > 0
           AND r.network = %s
           AND (

                ----- Include team owners

                (SELECT count(*)
                   FROM teams t
                  WHERE t.owner = p.username
                    AND t.is_approved IS TRUE
                    AND t.is_closed IS NOT TRUE
                 ) > 0


                OR -- Include green-lit Gratipay 1.0 balances

                p.status_of_1_0_balance='pending-payout'


                ----- TODO: Include members on payroll once process_payroll is implemented

               )
    """, (network,))

    # Work around lack of proper nesting in postgres.orm.
    out = []
    for participant, route in hack:
        route.__dict__['participant'] = participant
        out.append(route)

    return out


def record_exchange(db, route, amount, fee, participant, status, error=None):
    """Given a Bunch of Stuff, return an int (exchange_id).

    Records in the exchanges table have these characteristics:

        amount  It's negative for credits (representing an outflow from
                Gratipay to you) and positive for charges.
                The sign is how we differentiate the two in, e.g., the
                history page.

        fee     The payment processor's fee. It's always positive.

    """

    with db.get_cursor() as cursor:

        exchange_id = cursor.one("""
            INSERT INTO exchanges
                   (amount, fee, participant, status, route, note)
            VALUES (%s, %s, %s, %s, %s, %s)
         RETURNING id
        """, (amount, fee, participant.username, status, route.id, error))

        if status == 'failed':
            propagate_exchange(cursor, participant, route, error, 0)
        elif amount < 0:
            amount -= fee
            propagate_exchange(cursor, participant, route, '', amount)

    return exchange_id


def record_exchange_result(db, exchange_id, status, error, participant):
    """Updates the status of an exchange.
    """
    with db.get_cursor() as cursor:
        amount, fee, username, route = cursor.one("""
            UPDATE exchanges e
               SET status=%(status)s
                 , note=%(error)s
             WHERE id=%(exchange_id)s
               AND status <> %(status)s
         RETURNING amount, fee, participant
                 , ( SELECT r.*::exchange_routes
                       FROM exchange_routes r
                      WHERE r.id = e.route
                   ) AS route
        """, locals())
        assert participant.username == username
        assert isinstance(route, ExchangeRoute)

        if amount < 0:
            amount -= fee
            amount = amount if status == 'failed' else 0
            propagate_exchange(cursor, participant, route, error, -amount)
        else:
            amount = amount if status == 'succeeded' else 0
            propagate_exchange(cursor, participant, route, error, amount)


def propagate_exchange(cursor, participant, route, error, amount):
    """Propagates an exchange's result to the participant's balance and the
    route's status.
    """
    route.update_error(error or '', propagate=False)
    new_balance = cursor.one("""
        UPDATE participants
           SET balance=(balance + %s)
         WHERE id=%s
     RETURNING balance
    """, (amount, participant.id))

    if amount < 0 and new_balance < 0:
        raise NegativeBalance

    if hasattr(participant, 'set_attributes'):
        participant.set_attributes(balance=new_balance)
