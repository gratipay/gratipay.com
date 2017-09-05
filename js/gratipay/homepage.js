Gratipay.homepage = {}

Gratipay.homepage.initForm = function () {
    $form = $('#homepage #content form');
    $button = $form.find('button');
    $button.on('click', Gratipay.homepage.submitForm);

    braintree.dropin.create({
      authorization: 'sandbox_cr9dyy9c_bk8h97tqzyqjhtfn',
      container: '#braintree-container'
    }, function (createErr, instance) {
      $button.click(function () {
        instance.requestPaymentMethod(function (requestPaymentMethodErr, payload) {
          // Submit payload.nonce to your server
        });
      });
    });
}

Gratipay.homepage.submitForm = function (e) {
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
        error: [Gratipay.error, function () { $input.prop('disable', false); }]
    });
}
