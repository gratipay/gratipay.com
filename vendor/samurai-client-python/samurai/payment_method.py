"""
    Payment method.
    ~~~~~~~~~~~~~~~

    Encapsulation for the stored payment data, and payment methods.
"""
from api_base import ApiBase
from request import Request, fetch_url
from xmlutils import dict_to_xml

class PaymentMethod(ApiBase):
    """
    Proxy for samurai api payment method endpoints.
    Implements `find`, `retain`, `redact` and other related operations.

    This object makes available the response retured from the api.
    ::
        <payment_method>
            <payment_method_token>QhLaMNNpvHwfnFbHbUYhNxadx4C</payment_method_token>
            <created_at type="datetime">2011-02-12T20:20:46Z</created_at>
            <updated_at type="datetime">2011-04-22T17:57:30Z</updated_at>
            <custom>Any value you want us to save with this payment method.</custom>
            <is_retained type="boolean">true</is_retained>
            <is_redacted type="boolean">false</is_redacted>
            <is_sensitive_data_valid type="boolean">false</is_sensitive_data_valid>
            <messages>
            <message class="error" context="input.cvv" key="too_long" />
            <message class="error" context="input.card_number" key="failed_checksum" />
            </messages>
            <last_four_digits>1111</last_four_digits>
            <card_type>visa</card_type>
            <first_name>Bob</first_name>
            <last_name>Smith</last_name>
            <expiry_month type="integer">1</expiry_month>
            <expiry_year type="integer">2020</expiry_year>
            <address_1 nil="true"></address_1>
            <address_2 nil="true"></address_2>
            <city nil="true"></city>
            <state nil="true"></state>
            <zip nil="true"></zip>
            <country nil="true"></country>
        </payment_method>

    All xml elements inside top level element are directly accessible on the object.
    ::
        pm = PaymentMethod.find(token)
        pm.is_redcated
        pm.state

    The attributes are created on demand, and exist only if the element exists in the xml object
    wraps.

    Errors while operating on it will be accessible `errors`. If there aren't any errors, `errors`
    is False. If there are errors, `errors` is a list of errors.
    """
    top_xml_key = 'payment_method'

    find_url  = 'https://api.samurai.feefighters.com/v1/payment_methods/%s.xml'
    retain_url = 'https://api.samurai.feefighters.com/v1/payment_methods/%s/retain.xml'
    redact_url = 'https://api.samurai.feefighters.com/v1/payment_methods/%s/redact.xml'
    create_url = 'https://api.samurai.feefighters.com/v1/payment_methods.xml'
    update_url  = 'https://api.samurai.feefighters.com/v1/payment_methods/%s.xml'

    create_data = set(('card_number', 'cvv', 'expiry_month', 'expiry_year',
                       'first_name', 'last_name', 'address_1', 'address_2',
                       'city', 'state', 'zip', 'custom', 'sandbox'))

    def __init__(self, xml_res):
        super(PaymentMethod, self).__init__()
        self._xml_res = xml_res
        self._update_fields(xml_res)

    @classmethod
    def find(cls, payment_method_token):
        """
        Gets the payment method details.
        Returns xml data returned from the endpoint converted to python dictionary.
        ::
            pm = PaymentMethod.find(token)
            if not pm.errors:
                # Work on pm object here
            else:
                # pm.errors will be a list of errors
        """
        req = Request(cls.find_url % payment_method_token)
        return cls(fetch_url(req))

    def retain(self):
        """
        Issues `retain` call to samurai API.
        ::
            pm = PaymentMethod.find(token)
            if not pm.retain().is_retain:
                # Some thing prevented the retention.
                # Check pm.errors
            else:
                # Successfully redacted.
        """
        req = Request(self.retain_url % self.payment_method_token, method='post')
        res = fetch_url(req)
        self._update_fields(res)
        return self

    def redact(self):
        """
        Issues `redact` call to samurai API.
        ::
            pm = PaymentMethod.find(token)
            if not pm.redact().is_redacted:
                # Some thing prevented the redaction.
                # Check pm.errors
            else:
                # Successfully redacted.
        """
        req = Request(self.redact_url % self.payment_method_token, method='post')
        res = fetch_url(req)
        self._update_fields(res)
        return self

    @classmethod
    def create(cls, card_number, cvv, expiry_month, expiry_year, **other_args):
        """
        Creates a payment method.

        Transparent redirects are favored method for creating payment methods.
        Using this call places the burden of PCI compliance on the client since the
        data passes through it.
        ::
            pm = PaymentMethod.create('4242424242424242', '133', '07', '12')
            assert pm.is_sensitive_data_valid
        """
        payload = {
            'payment_method': {
                'card_number': card_number,
                'cvv': cvv,
                'expiry_month': expiry_month,
                'expiry_year': expiry_year,
            }
        }
        optional_data = dict((k, v) for k, v in other_args.iteritems()
                             if k in cls.create_data)
        payload['payment_method'].update(**optional_data)
        payload = dict_to_xml(payload)

        # Send payload and return payment method.
        req = Request(cls.create_url, payload, method='post')
        req.add_header("Content-Type", "application/xml")
        return cls(fetch_url(req))

    def update(self, **other_args):
        """
        Updates a payment method.

        Payment method can't be updated once it has been retained or redacted.
        ::
            pm = PaymentMethod.create('4242424242424242', '133', '07', '12')
            assert pm.is_sensitive_data_valid
            pm.update(first_name='dummy')
            if not pm.errors:
                assert pm.first_name == 'dummy'
            else:
                # deal with pm.errors
        """
        payload = {
            'payment_method': {
            }
        }
        optional_data = dict((k, v) for k, v in other_args.iteritems()
                             if k in self.create_data)
        payload['payment_method'].update(**optional_data)
        payload = dict_to_xml(payload)

        # Send payload and return payment method.
        req = Request(self.update_url % self.payment_method_token, payload, method='put')
        req.add_header("Content-Type", "application/xml")
        res = fetch_url(req)
        self._update_fields(res)
        return self
