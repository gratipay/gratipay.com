Gratipay.homepage = {}

Gratipay.homepage.initForm = function(clientAuthorization) {
    var self = this;
    self.$form = $('#homepage #content form');
    self.$submit = self.$form.find('button[type=submit]');

    $('a.what-why').click(function(e) {
        e.preventDefault();
        $('#what-why').slideToggle();
    });

    function disable(e) {
        e.preventDefault();
        self.$submit.prop('disabled', true);
        self.$submit.addClass('processing');
    }

    if (clientAuthorization === undefined) {    // Offline mode

        $('#braintree-container').addClass('offline').html(Gratipay.jsonml(['div',
            ['div', {'class': 'field amount'},
                ['input', {'id': 'nonce', 'value': 'fake-valid-nonce', 'required': true}, 'Nonce'],
            ],
            ['p', {'class': 'fine-print'}, "If you're seeing this on gratipay.com, we screwed up."]
        ]));

        self.$submit.click(function(e) {
            disable(e);
            nonce = $('#braintree-container input').val();
            self.submitFormWithNonce(nonce);
        });

    } else {                                    // Online mode (sandbox or production)

        function braintreeInitCallback(createErr, instance) {
            if (createErr) {
                $('#braintree-container').addClass('failed').text('Failed to load Braintree.');
            } else {
                self.$submit.click(function(e) {
                    disable(e);
                    instance.requestPaymentMethod(function(requestPaymentMethodErr, payload) {
                        self.submitFormWithNonce(payload ? payload.nonce : '');
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
    var self = this;
    var data = new FormData(self.$form[0]);
    data[data.set ? 'set' : 'append']('payment_method_nonce', nonce);
       // Chrome/FF || Safari

    $.ajax({
        url: self.$form.attr('action'),
        type: 'POST',
        data: data,
        processData: false,
        contentType: false,
        dataType: 'json',
        success: function(data) {
            // Due to Aspen limitations we use 200 for both success and failure. :/
            if (data.errors.length > 0) {
                self.$submit.prop('disabled', false);
                self.$submit.removeClass('processing');
                Gratipay.notification(data.msg, 'error');

                // The user could be submitting the form after fixing an error.
                // Let's first clear all errors, and then assign them again
                // based on the response received.
                self.$form.find('.error').removeClass('error');
                for (var i=0, fieldName; fieldName=data.errors[i]; i++) {
                    $('.'+fieldName, self.$form).addClass('error');
                }
            } else {
                Gratipay.notification.clear();
                $('.payment-complete a.invoice').attr('href', data.invoice_url);
                $('#banner h1 .pending').fadeOut(250, function() {
                    $('#banner h1 .complete').fadeIn(250)
                });
                $('.rollup').slideUp(500, function() {
                    $('.payment-complete').fadeIn(500);
                });
            }
        }
    });
};
