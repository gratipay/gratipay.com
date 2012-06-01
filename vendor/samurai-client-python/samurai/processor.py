"""
    Payment processor for simple purchases.
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Handles purchases.

    Simple purchases are done in a single step and there isn't an option to authorize
    or rollback it.

    Complex purchases are authorized first, and then can be rolled back or completed.
"""
import config
from xmlutils import dict_to_xml
from request import Request, fetch_url
from api_base import ApiBase
from transaction import Transaction

class Descriptor(object):
    """
    Descriptor to enable both class and instance method calls.
    """
    def __init__(self, name):
        self.name = name

    def __get__(self, instance, cls):
        if not instance:
            instance = cls.the_processor
        return getattr(instance, self.name)

class TheProcessor(object):
    """
    Constructs default processor.
    """
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def __get__(self, instance, cls):
        """
        This embodies the 'default processor' construction logic.
        Currently the only detail needed for 'default processor' is the processor token.
        """
        return cls(*self.args, **self.kwargs)

class Processor(ApiBase):
    """
    `Processor` deals with payments.

    The result of the operations is a transaction object. See documentation for `Transaction`
    to see the operations possible on transactions.

    """
    purchase_url = 'https://api.samurai.feefighters.com/v1/processors/%s/purchase.xml'
    authorize_url = 'https://api.samurai.feefighters.com/v1/processors/%s/authorize.xml'

    purchase_optional_data = set(('billing_reference', 'customer_reference',
                                 'descriptor', 'custom', 'description',
                                 'descriptor_name', 'descriptor_phone'))

    def __init__(self, processor_token):
        self.processor_token = processor_token

    #: The default processor.
    the_processor = TheProcessor(processor_token=config.processor_token)

    purchase = Descriptor('_purchase')
    def _purchase(self, payment_method_token, amount, processor_token=None, **options):
        """
        Makes a simple purchase call and returns a transaction object.
        ::
            transaction = Processor.purchase(payment_method_token, amount)

            # Follwing additional parameters can be passed while make a purchase call.
            # billing_reference: Custom identifier for this transaction in your application
            # customer_reference: Custom identifier for this customer in your application
            # descriptor: Custom descriptor here if your processor supports it
            # custom: Any value you like.  Will be passed to your processor for tracking.

            transaction = Processor.purchase(payment_method_token, amount,
                                             billing_reference=billing_reference,
                                             customer_reference=customer_reference,
                                             descriptor=descripton,
                                             custom=custom)

        """
        if not processor_token:
            processor_token = getattr(self, 'processor_token', None) or config.processor_token
        return self._transact(payment_method_token, amount, processor_token,
                            'purchase', self.purchase_url, options)

    authorize = Descriptor('_authorize')
    def _authorize(self, payment_method_token, amount, processor_token=None, **options):
        """
        `authorize` doesn't charge credit card. It only reserves the transaction amount.
        It returns a `Transaction` object which can be `captured` or `reversed`.

        It takes the same parameter as the `purchase` call.
        """
        if not processor_token:
            processor_token = getattr(self, 'processor_token', None) or config.processor_token
        return self._transact(payment_method_token, amount, processor_token,
                            'authorize', self.authorize_url, options)

    def _transact(self, payment_method_token, amount, processor_token,
                  transaction_type, endpoint, options):
        """
        Meant to be used internally and shouldn't be called from outside.

        Makes an `authorize` or `purchase` request.

        `authorize` and `purchase` have same flow, except for `transaction_type` and
        `endpoint`.
        """
        purchase_data = self._construct_options(payment_method_token, transaction_type,
                                              amount, options)
        # Send payload and return transaction.
        req = Request(endpoint % processor_token, purchase_data, method='post')
        req.add_header("Content-Type", "application/xml")
        return Transaction(fetch_url(req))

    def _construct_options(self, payment_method_token, transaction_type,
                           amount, options):
        """
        Constructs XML payload to be sent for the transaction.
        """
        # Pick relevant options and construct xml payload.
        purchase_data = {
            'transaction': {
                'type': transaction_type,
                'currency_code': 'USD',
                'amount': amount
            }
        }
        options = dict((k, v) for k, v in options.iteritems()
                       if k in self.purchase_optional_data)
        options['payment_method_token'] = payment_method_token
        purchase_data['transaction'].update(options)
        purchase_data = dict_to_xml(purchase_data)
        return purchase_data
