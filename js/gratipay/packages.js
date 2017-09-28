Gratipay.packages = {};

Gratipay.packages.initBulk = function() {
    $('.important-button button.apply').on('click', Gratipay.packages.postBulk);
};

Gratipay.packages.initSingle = function() {
    Gratipay.Select('.gratipay-select', Gratipay.packages.selectOne);
    $('.important-button button').on('click', Gratipay.packages.postOne);
    Gratipay.packages.selectOne($('.gratipay-select li.selected'));
};

Gratipay.packages.selectOne = function($li) {
    var action = $li.data('action');
    $('.important-button span').hide();
    $('.important-button span.' + action).show();
};

Gratipay.packages.postBulk = function(e) {
    e.preventDefault();
    var pkg, email, package_id, package_ids_by_email={};
    $('table.listing td.item ').not('.disabled').each(function() {
        pkg = $(this).data();
        if (package_ids_by_email[pkg.email] === undefined)
            package_ids_by_email[pkg.email] = [];
        package_ids_by_email[pkg.email].push(pkg.packageId);
    });
    for (email in package_ids_by_email)
        Gratipay.packages.post(email, package_ids_by_email[email], 'yes');
};

Gratipay.packages.postOne = function(e) {
    e.preventDefault();
    var $input = $('input[name=email]:checked');
    var email = $input.val();
    var package_ids;
    var show_address_in_message = 'no';
    if ($input.closest('li').data('action') === 'apply') {
        package_ids = [$('input[name=package_id]').val()];
        show_address_in_message = 'yes';
    }
    Gratipay.packages.post(email, package_ids, show_address_in_message);
}

Gratipay.packages.post = function(email, package_ids, show_address_in_message) {
    var action = 'start-verification';
    var $button = $('.important-button button')

    $button.prop('disabled', true);
    function reenable() { $button.prop('disabled', false); }
    $.ajax({
        url: '/~' + Gratipay.username + '/emails/modify.json',
        type: 'POST',
        data: { action: action
              , address: email
              , package_id: package_ids
              , show_address_in_message: show_address_in_message
               },
        traditional: true,
        dataType: 'json',
        success: function (msg) {
            if (msg) {
                Gratipay.notification(msg, 'success');
                reenable();
            }
        },
        error: [
            reenable,
            Gratipay.error
        ],
    });
};
