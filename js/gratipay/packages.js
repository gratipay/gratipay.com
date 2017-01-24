Gratipay.packages = {};

Gratipay.packages.post = function(e) {
    e.preventDefault();
    var $this = $(this);
    var action = 'add-email-and-claim-package';
    var package_id = $('input[name=package_id]').val();
    var email = $('input[name=email]:checked').val();

    var $inputs = $('input, button');
    $inputs.prop('disabled', true);

    $.ajax({
        url: '/~' + Gratipay.username + '/emails/modify.json',
        type: 'POST',
        data: {action: action, address: email, package_id: package_id},
        dataType: 'json',
        success: function (msg) {
            if (msg) {
                Gratipay.notification(msg, 'success');
            }
            $inputs.prop('disabled', false);
        },
        error: [
            function () { $inputs.prop('disabled', false); },
            Gratipay.error
        ],
    });
};
