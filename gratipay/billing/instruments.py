import braintree
import balanced

class CreditCard:
    def __init__(self, *args, **kwargs):
        fields = [
            'number',
            'expiration_year',
            'expiration_month',
            'address_postal_code',
            'cardholder_name'
        ]
        for field in fields:
            setattr(self, field, kwargs.pop(field, ''))

    @classmethod
    def from_route(cls, route):
        if route.network == 'braintree-cc':
            card = braintree.PaymentMethod.find(route.address)
            return cls(
                number=card.masked_number,
                expiration_month=card.expiration_month,
                expiration_year=card.expiration_year,
                address_postal_code=card.billing_address.postal_code,
                cardholder_name=card.cardholder_name
            )
        else:
            assert route.network == 'balanced-cc'
            card = balanced.Card.fetch(route.address)
            return cls(
                number=card.number,
                expiration_month=card.expiration_month,
                expiration_year=card.expiration_year,
                address_postal_code=card.address['postal_code'],
                cardholder_name=card.name
            )
