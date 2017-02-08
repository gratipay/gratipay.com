Gratipay.packages = {};

Gratipay.packages.post = function(e) {
    e.preventDefault();
    var $this = $(this);
    var action = 'add-email-and-claim-package';
    var $inputs = $('input, button');
    var $selection = $('input[name=email]:checked');
    var address = $selection.val();
    var package_id = $selection.parent().parent().data('package-id');

    $inputs.prop('disabled', true);

    $.ajax({
        url: '/~' + Gratipay.username + '/emails/modify.json',
        type: 'POST',
        data: {action: action, address: address, package_id: package_id},
        dataType: 'json',
        success: function (msg) {
            if (msg) {
                Gratipay.notification(msg, 'success');
            }
            if (action == 'add-email') {
                $('input.add-email').val('');
                setTimeout(function(){ window.location.reload(); }, 3000);
                return;
            }
            $inputs.prop('disabled', false);
        },
        error: [
            function () { $inputs.prop('disabled', false); },
            Gratipay.error
        ],
    });
};
