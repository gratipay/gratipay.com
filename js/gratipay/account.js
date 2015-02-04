Gratipay.account = {};

Gratipay.account.post_email = function(e) {
    e.preventDefault();
    var $this = $(this);
    var action = this.className;
    var $inputs = $('.emails button, .emails input');
    console.log($this);
    var address = $this.parent().data('email') || $('input.add-email').val();

    $inputs.prop('disabled', true);

    $.ajax({
        url: '../emails/modify.json',
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
        error: function (e) {
            $inputs.prop('disabled', false);
            error_message = JSON.parse(e.responseText).error_message_long;
            Gratipay.notification(error_message || "Failure", 'error');
        },
    });
};

Gratipay.account.init = function() {

    // Wire up username.
    // =================

    Gratipay.forms.jsEdit({
        hideEditButton: true,
        root: $('.username.js-edit'),
        success: function(d) {
            window.location.href = "/" + encodeURIComponent(d.username) + "/account/";
            return false;
        },
    });


    // Wire up account type.
    // =====================

    $('.number input').click(function(e) {
        var $input = $(this);

        e.preventDefault();

        function post(confirmed) {
            jQuery.ajax({
                url: '../number.json',
                type: 'POST',
                data: {
                    number: $input.val(),
                    confirmed: confirmed
                },
                success: function(data) {
                    if (data.confirm) {
                        if (confirm(data.confirm)) return post(true);
                        return;
                    }
                    if (data.number) {
                        $input.prop('checked', true);
                        Gratipay.notification(data.msg || "Success", 'success');
                        $('li.members').toggleClass('hidden', data.number !== 'plural');
                    }
                },
                error: function(r) {
                    Gratipay.notification(JSON.parse(r.responseText).error_message_long, 'error');
                }
            });
        }
        post();
    });


    // Wire up email addresses list.
    // =============================

    $('.emails button, .emails input').prop('disabled', false);
    $('.emails button[class]').on('click', Gratipay.account.post_email);
    $('form.add-email').on('submit', Gratipay.account.post_email);


    // Wire up API key.
    // ================

    var callback = function(data) {
        $('.api-key span').text(data.api_key || 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx');

        if (data.api_key) {
            $('.api-key').data('api-key', data.api_key);
            $('.api-key .show').hide();
            $('.api-key .hide').show();
        } else {
            $('.api-key .show').show();
            $('.api-key .hide').hide();
        }
    }

    $('.api-key').on('click', '.show', function() {
        if ($('.api-key').data('api-key'))
            callback({api_key: $('.api-key').data('api-key')});
        else
            $.get('../api-key.json', {action: 'show'}, callback);
    })
    .on('click', '.hide', callback)
    .on('click', '.recreate', function() {
        $.post('../api-key.json', {action: 'show'}, callback);
    });


    // Wire up privacy settings.
    // =========================

    $('.privacy input').each(function() {
        var $input = $(this);
        var field = $input.attr('name');
        var is_checkbox = $input.attr('type') === 'checkbox';

        $(this).click(function() {

            if (is_checkbox)
                var value = $input.prop('checked').toString();
            else
                var value = $input.attr('value');
            console.log(field, value);

            jQuery.ajax(
                { url: './privacy'
                , type: 'POST'
                , data: {field: field, value: value}
                , dataType: 'text'
                , success: function(data) {
                    if (is_checkbox)
                        $input.attr('checked', data[field]);
                    else    // assumed to be a radio
                        $('[value=' + data[field]).prop('checked', true);
                    Gratipay.notification("Privacy preferences updated.", "success");
                }
                , error: function() {
                    Gratipay.notification( "Sorry, we failed to update your privacy preferences."
                                         , "error"
                                          );
                }
            });
        });
    });


    // Wire up close account.
    // ======================

    $('button.close-account').click(function() {
        window.location.href = './close';
    });
};
