"""
    Transaction
    ~~~~~~~~~~~~

    Transactions encapsulate the returned data from the api when a transaction is made
    agains a payment token.
"""
from xmlutils import dict_to_xml
from api_base import ApiBase
from request import Request, fetch_url
from errors import UnauthorizedTransactionError

class Transaction(ApiBase):
    """
    A completed or authorized transaction.
    This class can be used to introspect trasnaction data, as well as perform transaction
    operations viz. reverse, authorize, capture etc.

    In case of simple purchases, the returned data will be mostly used for inspection.

    In complex transactions, opertaions on it are used to perform or cancel it.
    ::
        <transaction>
            <reference_id>3dcFjTC7LDjIjTY3nkKjBVZ8qkZ</reference_id>
            <transaction_token>53VFyQKYBmN9vKfA9mHCTs79L9a</transaction_token>
            <created_at type="datetime">2011-04-22T17:57:56Z</created_at>
            <descriptor>Custom descriptor here if your processor supports it.</descriptor>
            <custom>Any value you like.</custom>
            <transaction_type>purchase</transaction_type>
            <amount>100.00</amount>
            <currency_code>USD</currency_code>
            <billing_reference>12345678</billing_reference>
            <customer_reference>1234</customer_reference>
            <processor_token>[Processor Token]</processor_token>
            <processor_response>
                <success type="boolean">false</success>
                <messages>
                <message class="error" context="processor.avs" key="country_not_supported" />
                <message class="error" context="input.cvv" key="too_short" />
                </messages>
            </processor_response>
            <payment_method>...</payment_method>
        </transaction>

    All elements inside root element `transaction` are directly available on the object.
    """
    top_xml_key = 'transaction'

    find_url = 'https://api.samurai.feefighters.com/v1/transactions/%s.xml'
    capture_url = 'https://api.samurai.feefighters.com/v1/transactions/%s/capture.xml'
    reverse_url = 'https://api.samurai.feefighters.com/v1/transactions/%s/reverse.xml'
    credit_url = 'https://api.samurai.feefighters.com/v1/transactions/%s/credit.xml'
    void_url = 'https://api.samurai.feefighters.com/v1/transactions/%s/void.xml'

    def __init__(self, xml_res):
        """
        Initializes transaction data by parsing `xml_res`.
        """
        super(Transaction, self).__init__()
        self._update_fields(xml_res)

    @classmethod
    def find(cls, reference_id):
        """
        Gets the transaction details.
        Returns xml data returned from the endpoint converted to python dictionary.
        ::
            trans = Transaction.find(reference_id)
            if not trans.errors:
                # Operate on transaction object
            else:
                # Work on list of errors in trans.errors
        """
        req = Request(cls.find_url % reference_id)
        return cls(fetch_url(req))

    def _message_block(self, parsed_res):
        """
        Returns the message block from the `parsed_res`
        """
        return (parsed_res.get(self.top_xml_key) and
                parsed_res[self.top_xml_key].get('processor_response') and
                parsed_res[self.top_xml_key]['processor_response'].get('messages'))

    def _check_semantic_errors(self, parsed_res):
        """
        Checks `parsed_res` for error blocks.
        If the transaction failed, sets `self.errors`
        Else delegates to superclass.
        """
        if parsed_res.get(self.top_xml_key):
            if not parsed_res[self.top_xml_key]['processor_response']['success']:
                message_block = self._message_block(parsed_res)
                if message_block and message_block.get('message'):
                    message = message_block['message']
                    self.errors = message if isinstance(message, list) else [message]
                    self.errors = filter(lambda m: m['subclass']=='error', self.errors)
                return True
        return super(Transaction, self)._check_semantic_errors(parsed_res)

    def is_success(self):
        """
        Returns True if the transaction succeeded.

        You are better of checking `trans.errors`

        """
        if (getattr(self, 'processor_response') and self.processor_response.get('success')
            and self.processor_response['success']):
            return True
        return False

    def is_declined(self):
        """
        Returns True if the transaction is declined.

        You are better off checking `trans.errors`
        """
        message_block = self._message_block
        if message_block and message_block.get('message'):
            messages = message_block['message']
            return any(True for m in messages if isinstance(m, dict)
                       and m.get('key') == 'declined')
        return False

    def capture(self, amount):
        """
        Captures transaction. Works only if the transaction is authorized.

        Returns a new transaction.
        ::
            trans = Processor.authorize(payment_method_token, amount)
            trans = trans.capture(amount)
            if not trans.errors:
                # Capture successful
            else:
                # Work on list of errors in trans.errors

        """
        return self._transact(self.capture_url, amount)

    def credit(self, amount):
        """
        Credits transaction. Works only if the transaction is authorized.
        Depending on the settlement status of the transaction, and the behavior of the
        processor endpoint, this API call may result in a `void`, `credit`, or `refund`.

        Returns a new transaction.
        ::
            trans = Processor.authorize(payment_method_token, amount)
            trans = trans.credit(amount)
            if not trans.errors:
                # Capture successful
            else:
                # Work on list of errors in trans.errors

        """
        return self._transact(self.credit_url, amount)

    def reverse(self, amount=None):
        """
        Reverses transaction. Works only if the transaction is authorized.

        Returns a new transaction.

        The `amount` field is optional. If left blank, the whole transaction is reversed.
        """
        if not amount:
          amount = self.amount
        return self._transact(self.reverse_url, amount)

    def void(self):
        """
        Voids transaction. Works only if the transaction is authorized.

        Returns a new transaction.
        """
        return self._transact(self.void_url)

    def _transact(self, endpoint, amount=None):
        """
        Meant to be used internally and shouldn't be called from outside.

        Makes the specified call and returns resultant `transaction`.
        """
        if not getattr(self, 'transaction_token', None):
            raise UnauthorizedTransactionError('Transaction token is missing. Only authorized'
                                               'transactions can make this call.')
        if amount:
            data = dict_to_xml({'transaction':{'amount': amount}})
            req = Request(endpoint % self.transaction_token, data, method='post')
        else:
            req = Request(endpoint % self.transaction_token, method='post')
        res = fetch_url(req)
        return type(self)(res)
