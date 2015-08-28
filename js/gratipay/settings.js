Gratipay.settings = {};

Gratipay.settings.init = function() {

    // Wire up username knob.
    // ======================

    Gratipay.forms.jsEdit({
        hideEditButton: true,
        root: $('.username.js-edit'),
        success: function(d) {
            window.location.href = "/" + encodeURIComponent(d.username) + "/settings/";
            return false;
        },
    });


    // Wire up account type knob.
    // ==========================

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
                error: Gratipay.error,
            });
        }
        post();
    });

    // Wire up privacy settings.
    // =========================

    $('.privacy-settings input[type=checkbox]').click(function(e) {
        var neg = false;
        var field = $(e.target).data('field');
        if (field[0] == '!') {
            neg = true;
            field = field.substr(1);
        }
        jQuery.ajax(
            { url: '../privacy.json'
            , type: 'POST'
            , data: {toggle: field}
            , dataType: 'json'
            , success: function(data) {
                if (data.msg) {
                    Gratipay.notification(data.msg, 'success');
                }
                $(e.target).attr('checked', data[field] ^ neg);
            }
            , error: Gratipay.error
        });
    });

    // Wire up API Key
    // ===============

    var callback = function(data) {
        var val = data.api_key || 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx';
        $('.api-credentials .key span').text(val);

        if (data.api_key) {
            $('.api-credentials').data('key', data.api_key);
            $('.api-credentials .show').hide();
            $('.api-credentials .hide').show();
        } else {
            $('.api-credentials .show').show();
            $('.api-credentials .hide').hide();
        }
    }

    $('.api-credentials').on('click', '.show', function() {
        if ($('.api-credentials').data('key'))
            callback({api_key: $('.api-credentials').data('key')});
        else
            $.get('../api-key.json', {action: 'show'}, callback);
    })
    .on('click', '.hide', callback)
    .on('click', '.recreate', function() {
        $.post('../api-key.json', {action: 'show'}, callback);
    });


    // Wire up close knob.
    // ===================

    $('button.close-account').click(function() {
        window.location.href = './close';
    });
};
