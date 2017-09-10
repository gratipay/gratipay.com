Gratipay.homepage = {}

Gratipay.homepage.initForm = function(clientAuthorization) {
    $form = $('#homepage #content form');
    $submit = $form.find('button[type=submit]');

    if (clientAuthorization === undefined) {    // Offline mode

        $('#braintree-container').addClass('offline').html(Gratipay.jsonml(['div',
            ['div', {'class': 'field amount'},
                ['label', {'for': 'nonce'}, 'Nonce'],
                ['input', {'id': 'nonce', 'value': 'fake-valid-nonce', 'required': true}, 'Nonce'],
            ],
            ['p', {'class': 'fine-print'}, "If you're seeing this on gratipay.com, we screwed up."]
        ]));

        $submit.click(function(e) {
            e.preventDefault();
            nonce = $('#braintree-container input').val();
            Gratipay.homepage.submitFormWithNonce(nonce);
        });

    } else {                                    // Online mode (sandbox or production)

        function braintreeInitCallback(createErr, instance) {
            if (createErr) {
                $('#braintree-container').addClass('failed').text('Failed to load Braintree.');
            } else {
                $submit.click(function(e) {
                    e.preventDefault();
                    instance.requestPaymentMethod(function(requestPaymentMethodErr, payload) {
                        Gratipay.homepage.submitFormWithNonce(payload.nonce);
                    });
                });
            }
        }

        braintree.dropin.create({
            authorization: clientAuthorization,
            container: '#braintree-container'
        }, braintreeInitCallback);
    }
};


Gratipay.homepage.submitFormWithNonce = function(nonce) {
    $submit = $form.find('button[type=submit]');
    $form = $('#homepage #content form');
    var data = new FormData($form[0]);
    data.set('payment_method_nonce', nonce);

    $submit.prop('disable', true);

    $.ajax({
        url: $form.attr('action'),
        type: 'POST',
        data: data,
        processData: false,
        contentType: false,
        dataType: 'json',
        success: function(data) {
            // Due to Aspen limitations we use 200 for both success and failure. :/
            if (data.errors.length > 0) {
                $submit.prop('disable', false);
                Gratipay.notification(data.msg, 'error');
            } else {
                $('.payment-complete a.receipt').attr('href', data.receipt_url);
                $('.payment-complete').slideDown(200);
                $('form').slideUp(500);
            }
        }
    });
};
