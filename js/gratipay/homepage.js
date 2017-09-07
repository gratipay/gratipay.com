Gratipay.homepage = {}

Gratipay.homepage.initForm = function(clientAuthorization) {
    $form = $('#homepage #content form');

    $submit= $form.find('button[type=submit]');
    $submit.click(Gratipay.homepage.submitForm);

    $chooseEcosystem = $form.find('.ecosystem-chooser button');
    $chooseEcosystem.click(function(e) {
        e.preventDefault();
        Gratipay.notification('Not implemented.', 'error');
    });

    $promote = $form.find('.promotion-gate button');
    $promote.click(Gratipay.homepage.openPromote);

    braintree.dropin.create({
      authorization: clientAuthorization,
      container: '#braintree-container'
    }, function (createErr, instance) {
      $submit.click(function () {
        instance.requestPaymentMethod(function (requestPaymentMethodErr, payload) {
          // Submit payload.nonce to your server
        });
      });
    });
}

Gratipay.homepage.submitForm = function(e) {
    e.preventDefault();

    $input = $(this)
    $form = $(this).parent('form');
    var data = new FormData($form[0]);

    $input.prop('disable', true);

    $.ajax({
        url: $form.attr('action'),
        type: 'POST',
        data: data,
        processData: false,
        contentType: false,
        dataType: 'json',
        success: function (d) {
            $('a.team_url').attr('href', d.team_url).text(d.team_url);
            $('a.review_url').attr('href', d.review_url).text(d.review_url);
            $('form').slideUp(500, function() {
                $('.application-complete').slideDown(250);
            });
        },
        error: [Gratipay.error, function() { $input.prop('disable', false); }]
    });
}

Gratipay.homepage.openPromote = function(e) {
    e.preventDefault();
    $('.promotion-gate').fadeOut();
    $('.promotion-fields').slideDown(function() {
        $('.promotion-fields input:first').focus();
    });
}
