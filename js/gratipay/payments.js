Gratipay.payments = {};

Gratipay.payments.init = function() {

    Gratipay.forms.jsEdit({
        confirmBeforeUnload: true,
        hideEditButton: true,
        root: $('.your-payment.js-edit'),
        success: function(data) {
            Gratipay.notification(data.msg, 'success');
            Gratipay.payments.afterPaymentChange(data);
        }
    });

    $('.your-payment button.edit').click(function() {
        $('.your-payment input').focus();
    });

    $('.your-payment button.stop').click(function() {
        $('.your-payment input').val('0');
        $('.your-payment button.save').click();
    });

    $('.your-payment button.cancel').click(function() {
        $('.your-payment form').trigger('reset');
    });

    // Cancel if the user presses the Escape key
    $('.your-payment input').keyup(function(e) {
        if (e.keyCode === 27)
            $('.your-payment button.cancel').click();
    });
};


Gratipay.payments.initSupportGratipay = function() {
    $('.support-gratipay button').click(function() {
        var amount = parseFloat($(this).attr('data-amount'), 10);
        Gratipay.payments.set('Gratipay', amount, function(data) {
            Gratipay.notification(data.msg, 'success');
            $('.support-gratipay').slideUp();

            // If you're on your own giving page ...
            var payment_on_giving = $('.your-payment[data-team="Gratipay"]');
            if (payment_on_giving.length > 0) {
                payment_on_giving[0].defaultValue = amount;
                payment_on_giving.attr('value', amount.toFixed(2));
            }
        });
    });

    $('.support-gratipay .no-thanks').click(function(event) {
        event.preventDefault();
        jQuery.post('/ride-free.json')
            .success(function() { $('.support-gratipay').slideUp(); })
            .fail(Gratipay.error)
    });
};


Gratipay.payments.afterPaymentChange = function(data) {
    $('.my-total-giving').text(data.total_giving_l);
    $('.total-receiving[data-team="'+data.team_id+'"]').text(data.total_receiving_team_l);
    $('#payment-prompt').toggleClass('needed', data.amount > 0);
    $('.nreceiving_from[data-team="'+data.team_id+'"]').text(data.nreceiving_from);

    var $your_payment = $('.your-payment[data-team="'+data.team_id+'"]');
    if ($your_payment) {
        var $input = $your_payment.find('input');
        $input[0].defaultValue = $input.val();
        $your_payment.find('span.amount').text(data.amount_l);
        $your_payment.find('.edit').toggleClass('not-zero', data.amount > 0);
        $your_payment.find('.stop').toggleClass('zero', data.amount === 0);
    }
};


Gratipay.payments.set = function(team, amount, callback) {

    // send request to set up a recurring payment
    $.post('/' + team + '/payment-instruction.json', { amount: amount }, function(data) {
        if (callback) callback(data);
        Gratipay.payments.afterPaymentChange(data);
    })
    .fail(Gratipay.error);
};
