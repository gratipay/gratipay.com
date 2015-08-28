Gratipay.emails = {};

Gratipay.emails.post = function(e) {
    e.preventDefault();
    var $this = $(this);
    var action = this.className;
    var $inputs = $('.emails button, .emails input');
    console.log($this);
    var address = $this.parent().data('email') || $('input.add-email').val();

    $inputs.prop('disabled', true);

    $.ajax({
        url: 'modify.json',
        type: 'POST',
        data: {action: action, address: address},
        dataType: 'json',
        success: function (msg) {
            if (msg) {
                Gratipay.notification(msg, 'success');
            }
            if (action == 'add-email') {
                $('input.add-email').val('');
                setTimeout(function(){ window.location.reload(); }, 3000);
                return;
            } else if (action == 'set-primary') {
                $('.emails li').removeClass('primary');
                $this.parent().addClass('primary');
            } else if (action == 'remove') {
                $this.parent().fadeOut();
            }
            $inputs.prop('disabled', false);
        },
        error: [
            function () { $inputs.prop('disabled', false); },
            Gratipay.error
        ],
    });
};


Gratipay.emails.init = function () {

    // Wire up email addresses list.
    // =============================

    $('.emails button, .emails input').prop('disabled', false);
    $('.emails button[class]').on('click', Gratipay.emails.post);
    $('form.add-email').on('submit', Gratipay.emails.post);


    // Wire up notification preferences
    // ================================

    $('.email-notifications input').click(function(e) {
        var field = $(e.target).data('field');
        var bits = $(e.target).data('bits') || 1;
        jQuery.ajax(
            { url: '../emails/notifications.json'
            , type: 'POST'
            , data: {toggle: field, bits: bits}
            , dataType: 'json'
            , success: function(data) {
                Gratipay.notification(data.msg, 'success');
                $(e.target).attr('checked', data.new_value & bits)
            }
            , error: [
                Gratipay.error,
                function(){ $(e.target).attr('checked', !$(e.target).attr('checked')) },
            ]
        });
    });
};
