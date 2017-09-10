Gratipay.homepage = {}

Gratipay.homepage.initForm = function(clientAuthorization) {
    var self = this;
    self.$form = $('#homepage #content form');
    self.$submit = self.$form.find('button[type=submit]');

    if (clientAuthorization === undefined) {    // Offline mode

        $('#braintree-container').addClass('offline').html(Gratipay.jsonml(['div',
            ['div', {'class': 'field amount'},
                ['label', {'for': 'nonce'}, 'Nonce'],
                ['input', {'id': 'nonce', 'value': 'fake-valid-nonce', 'required': true}, 'Nonce'],
            ],
            ['p', {'class': 'fine-print'}, "If you're seeing this on gratipay.com, we screwed up."]
        ]));

        self.$submit.click(function(e) {
            e.preventDefault();
            nonce = $('#braintree-container input').val();
            self.submitFormWithNonce(nonce);
        });

    } else {                                    // Online mode (sandbox or production)

        function braintreeInitCallback(createErr, instance) {
            if (createErr) {
                $('#braintree-container').addClass('failed').text('Failed to load Braintree.');
            } else {
                self.$submit.click(function(e) {
                    e.preventDefault();
                    instance.requestPaymentMethod(function(requestPaymentMethodErr, payload) {
                        self.submitFormWithNonce(payload.nonce);
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
    data.set('payment_method_nonce', nonce);

    self.$submit.prop('disable', true);

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
                self.$submit.prop('disable', false);
                Gratipay.notification(data.msg, 'error');
                for (var i=0, fieldName; fieldName=data.errors[i]; i++) {
                    $('.'+fieldName, self.$form).addClass('error');
                }
            } else {
                $('.payment-complete a.receipt').attr('href', data.receipt_url);
                $('form').slideUp(500, function() {
                    $('.payment-complete').fadeIn(500);
                });
            }
        }
    });
};
