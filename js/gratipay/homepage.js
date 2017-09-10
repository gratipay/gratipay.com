Gratipay.homepage = {}

Gratipay.homepage.initForm = function(clientAuthorization) {
    $form = $('#homepage #content form');

    function callback(createErr, instance) {
        $submit = $form.find('button[type=submit]');
        $submit.click(function(e) {
            e.preventDefault();
            instance.requestPaymentMethod(function(requestPaymentMethodErr, payload) {
                Gratipay.homepage.submitFormWithNonce(payload.nonce);
            });
        });
    }

    braintree.dropin.create({
      authorization: clientAuthorization,
      container: '#braintree-container'
    }, callback);
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
            console.log(data);
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
