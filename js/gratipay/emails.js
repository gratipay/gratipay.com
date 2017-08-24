Gratipay.emails = {};

Gratipay.emails.post = function() {
    var $this = $(this);
    var action = this.className;
    var $inputs = $('.emails button, .emails input');
    var $row = $this.closest('tr');
    var address = $row.data('email') || $('.add input').val();

    $inputs.prop('disabled', true);

    $.ajax({
        url: 'modify.json',
        type: 'POST',
        data: {action: action, address: address},
        dataType: 'json',
        success: function (msg) {
            switch(action) {
                case 'resend':
                    Gratipay.notification(msg, 'success');
                    break;
                default:
                    window.location.reload();
            };
            $inputs.prop('disabled', false);
        },
        error: [
            function () { $inputs.prop('disabled', false); },
            Gratipay.error
        ],
    });
};

Gratipay.emails.showAddForm = function() {
    $('.add-form-knob').hide();
    $('.add form').show();
}

Gratipay.emails.hideAddForm = function() {
    $('.add form').hide();
    $('.add-form-knob').show();
}

Gratipay.emails.handleAddForm = function(e) {
    e.preventDefault();
    if (e.type === 'submit')
        Gratipay.emails.post.call(this);
    else
        Gratipay.emails.hideAddForm();
}

Gratipay.emails.init = function() {

    // Wire up email addresses list.
    // =============================

    $('.emails button, .emails input').prop('disabled', false);
    $('.emails tr.existing button').click(Gratipay.emails.post);
    $('button.add').click(Gratipay.emails.showAddForm);
    $('.add form').on('submit reset', Gratipay.emails.handleAddForm);


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
