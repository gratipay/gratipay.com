import braintree
import balanced

class CreditCard:
    def __init__(self, *args, **kwargs):
        fields = [
            'card_type',
            'number',
            'expiration_year',
            'expiration_month',
            'address_line1',
            'address_line2',
            'address_city',
            'address_state',
            'address_postal_code',
            'address_country_code',
            'cardholder_name'
        ]
        for field in fields:
            setattr(self, field, kwargs.pop(field, ''))

    @classmethod
    def from_route(cls, route):
        if route.network == 'braintree-cc':
            card = braintree.PaymentMethod.find(route.address)
            return cls(
                card_type=card.card_type,
                number=card.masked_number,
                expiration_month=card.expiration_month,
                expiration_year=card.expiration_year,
                cardholder_name=card.cardholder_name,
                address_postal_code=card.billing_address.postal_code
            )
        else:
            assert route.network == 'balanced-cc'
            card = balanced.Card.fetch(route.address)
            return cls(
                card_type=card.brand,
                number=card.number,
                expiration_month=card.expiration_month,
                expiration_year=card.expiration_year,
                cardholder_name=card.name,
                address_line1=card.address['line1'],
                address_line2=card.address['line2'],
                address_city=card.address['city'],
                address_state=card.address['state'],
                address_postal_code=card.address['postal_code'],
                address_country_code=card.address['country_code'],
            )
