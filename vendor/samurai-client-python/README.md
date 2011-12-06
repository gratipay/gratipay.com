Samurai
=======

If you are an online merchant and using FeeFighters' Samurai gateway, this package will
make your life easy. Integrate with the samurai.feefighters.com portal and
process transactions.


Installation
------------

Install Samurai just like any other package.

    pip install "samurai"

On most of the systems, you will need the `sudo` permissions if you are doing a system wide
install.

    sudo pip install "samurai"


Configuration
-------------

Set options on `samurai.config` module before you use it. The api uses the keys set on this module.

    import samurai.config as config
    config.merchant_key = your_merchant_key
    config.merchant_password = your_merchant_password
    config.processor_token = processor_token

Samurai API Reference
---------------------

1. ###Overview

    The Samurai API uses simple XML payloads transmitted over 256-bit encrypted HTTPS POST with Basic Authentication. . This package encapsulates the API calls as simple method calls on PaymentMethod and Transaction models, so you shouldn't need to think about the details of the actual API.

2. ###Getting started

    To use the Samurai API, you'll need a Merchant Key, Merchant Password and a Processor Token. Sign up for an account to get started.

    Make sure you have configured the `merchant_key` and `merchant_password` as documented above before making any other
    api calls.


3. ###Payment Method

    Each time a user stores their billing information in the Samurai system, we call it a Payment Method.

    Our transparent redirect uses a simple HTML form on your website that submits your user’s billing information directly to us over SSL so that you never have to worry about handling credit card data yourself. We’ll quickly store the sensitive information, tokenize it for you and return the user to a page on your website of your choice with the new Payment Method Token.

    From that point forward, you always refer to the Payment Method Token anytime you’d like to use that billing information for anything.


    1. ####Fetching a Payment Method

        Since the transparent redirect form submits directly to Samurai, you don’t get to see the data that the user entered until you read it from us. This way, you can see if the user made any input errors and ask them to resubmit the transparent redirect form if necessary.

        We’ll only send you non-sensitive data, so you will no be able to pre-populate the sensitive fields (card number and cvv) in the resubmission form.

            from samurai.payment_method import PaymentMethod
            payment_method = PaymentMethod.find(payment_method_token)
            if not payment_method.errors:
                # Operate on valid `payment_method`
            else:
                # Check the errors. payment_method.errors will be a list of errors.


    2. ####Retaining a Payment Method

        Once you have determined that you’d like to keep a Payment Method in the Samurai vault, you must tell us to retain it. If you don’t explicitly issue a retain command, we will delete the Payment Method within 48 hours in order to comply with PCI DSS requirement 3.1, which states:

            "3.1 Keep cardholder data storage to a minimum. Develop a data retention and disposal policy. Limit storage amount and retention time to that which is required for business, legal, and/or regulatory purposes, as documented in the data retention policy."

        However, if you perform a purchase or authorize transaction with a Payment Method, it will be automatically retained for future use.

            from samurai.payment_method import PaymentMethod
            payment_method = PaymentMethod.find(payment_method_token)
            if payment_method.redact().is_redacted:
                # redacted
            else:
                # Check the errors. payment_method.errors will be a list of errors.


    3. ####Redacting a Payment Method

        It’s important that you redact payment methods whenever you know you won’t need them anymore. Typically this is after the credit card’s expiration date or when your user has supplied you with a different card to use.

            from samurai.payment_method import PaymentMethod
            payment_method = PaymentMethod.find(payment_method_token)
            if payment_method.retain().is_retained:
                # retained
            else:
                # Check the errors. payment_method.errors will be a list of errors.

4. ###Processing Payments (Simple)

    When you’re ready to process a payment, the simplest way to do so is with the purchase method.

        from samurai.processor import Processor
        trans = Processor.purchase(payment_method_token, amount)
        if not trans.errors:
            # successful
        else:
            # Check the errors. trans.errors will be a list of errors.

    The following optional parameters are available on a purchase transaction:

        * descriptor: descriptor for the transaction
        * custom: custom data, this data does not get passed to the processor, it is stored within api.samurai.feefighters.com only
        * customer_reference: an identifier for the customer, this will appear in the processor if supported
        * billing_reference: an identifier for the purchase, this will appear in the processor if supported


        trans = Processor.purchase(payment_method_token, amount,
                                descriptor=descriptor, custom=custom)


5. ###Processing Payments (Complex)

    In some cases, a simple purchase isn’t flexible enough. The alternative is to do an Authorize first, then a Capture if you want to process a previously authorized transaction or a Void if you want to cancel it. Be sure to save the transaction_token that is returned to you from an authorization because you’ll need it to capture or void the transaction.

    1. ####Authorize

        An Authorize doesn’t charge your user’s credit card. It only reserves the transaction amount and it has the added benefit of telling you if your processor thinks that the transaction will succeed whenever you Capture it.

            from samurai.processor import Processor
            trans = Processor.authorize(payment_method_token, amount)
            if not trans.errors:
                # successful
            else:
                # Check the errors. trans.errors will be a list of errors.

    2. ####Capture

        You can only execute a capture on a transaction that has previously been authorized. You’ll need the Transaction Token value from your Authorize command to construct the URL to use for capturing it.

            from samurai.processor import Processor
            trans = Processor.authorize(payment_method_token, amount)
            if not trans.errors:
                new_trans = trans.capture(amount)
                if not new_trans.errors:
                    # successful
            else:
                # Check the errors. trans.errors will be a list of errors.

    3. ####Reverse

        A reverse call cancels or refunds a previous transaction. You’ll need the Transaction Token value from your Authorize command to construct the URL to use for reversing it.

        The amount is optional. If omitted, then the entire transaction will be reversed.

        **Note: depending on the settlement status of the transaction, and the behavior of the processor endpoint, this API call may result in a Void, Credit, or Refund transaction.**

            from samurai.processor import Processor
            trans = Processor.authorize(payment_method_token, amount)
            if not trans.errors:
                new_trans = trans.reverse(amount)
                if not new_trans.errors:
                    # successful
            else:
                # Check the errors. trans.errors will be a list of errors.


    4. ####Void

        The void method is maintained for backwards-compatibility, but it is essentially an alias of the reverse API method. You’ll need the Transaction Token value from your Authorize command to construct the URL to use for voiding it.

        **Note: depending on the settlement status of the transaction, and the behavior of the processor endpoint, this API call may result in a Void, Credit, or Refund transaction.**

            from samurai.processor import Processor
            trans = Processor.authorize(payment_method_token, amount)
            if not trans.errors:
                new_trans = trans.void()
                if not new_trans.errors:
                    # successful
            else:
                # Check the errors. trans.errors will be a list of errors.


    5. ####Credit

        The credit method is maintained for backwards-compatibility, but it is essentially an alias of the reverse API method. You’ll need the Transaction Token value from your Authorize command to construct the URL to use for crediting it.

        **Note: depending on the settlement status of the transaction, and the behavior of the processor endpoint, this API call may result in a Void, Credit, or Refund transaction.**

            from samurai.processor import Processor
            trans = Processor.authorize(payment_method_token, amount)
            if not trans.errors:
                new_trans = trans.credit(amount)
                if not new_trans.errors:
                    # successful
            else:
                # Check the errors. trans.errors will be a list of errors.

    6. ####Fetching a Transaction

        Each time you use one of the transaction processing functions `(purchase, authorize, capture, void, credit)` you are given a `reference_id` that uniquely identifies the transaction for reporting purposes. If you want to retrieve transaction data, you can use this fetch method on the reference_id.

            from samurai.transaction import Transaction
            trans = Transaction.find(reference_id)
            if not trans.errors:
                # successful
            else:
                # Check the errors. trans.errors will be a list of errors.

5. ###Server-to-Server Payment Method API

    We don't typically recommend using our server-to-server API for creating/updating Payment Methods, because it requires credit card data to pass through your server and exposes you to a much greater PCI compliance & risk liability.

    However, there are situations where using the server-to-server API is appropriate, such as integrating a server that is already PCI-secure with Samurai or if you need to perform complex transactions and don't mind bearing the burden of greater compliance and risk.

    1. ####Creating a Payment Method (S2S)

            from samurai.payment_method import PaymentMethod
            pm = PaymentMethod.create('4242424242424242', '133', '07', '12')

    2. ####Updating a Payment Method (S2S)

            from samurai.payment_method import PaymentMethod
            pm = PaymentMethod.find(payment_method_token)
            pm.update(first_name='dummy')
            if not pm.errors:
                assert pm.first_name == 'dummy'
            else:
                # deal with pm.errors
