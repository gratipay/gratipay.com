Gratipay.homepage = {}

Gratipay.homepage.initForm = function () {
    $form = $('#homepage #content form');
    $submit= $form.find('button[type=submit]');
    $submit.click(Gratipay.homepage.submitForm);

    $promote = $form.find('.promotion-gate button');
    $promote.click(Gratipay.homepage.openPromote);

    braintree.dropin.create({
      authorization: 'sandbox_cr9dyy9c_bk8h97tqzyqjhtfn',
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

jQuery.fn.extend({
    toggleText:function(a,b){
        if(this.html()==a){
            this.html(b)
        } 
        else {
            this.html(a)
            $('#promotion-fields :input').val('');
        }
    }
});

Gratipay.homepage.openPromote = function(e) {
    e.preventDefault();
    $('.promotion-fields').slideToggle(function() {
        $('.promotion-fields input:first').focus();
        $('#toggle').toggleText('Provide Promotion Details','Cancel');
    });
}
