$(document).ready(function() {

    // Wire up is_suspicious toggle.
    // =============================

    $('.is-suspicious-label input').change(function() {
        var username = $(this).attr('data-username');
        jQuery.ajax({
            url: '/~' + username + '/toggle-is-suspicious.json',
            type: 'POST',
            dataType: 'json',
            success: function (data) {
                $('.avatar').toggleClass('is-suspicious', data.is_suspicious);
                $('.is-suspicious-label input').prop('checked', data.is_suspicious);
            },
            error: Gratipay.error,
        });
    });


    // Wire up 1.0 payout status toggle.
    // =================================

    $('select.payout-1-0').change(function() {
        var username = $(this).attr('data-username');
        jQuery.ajax({
            url: '/~' + username + '/payout-status.json',
            type: 'POST',
            data: {to: $(this).val()},
            dataType: 'json',
            success: function (data) {
                Gratipay.notification( "1.0 payout status set to '" + data.status + "'."
                                     , 'success'
                                      );
            },
            error: Gratipay.error,
        });
    });

});
