Gratipay.packages = {};

Gratipay.packages.initBulk = function() {
    $('button.apply').on('click', Gratipay.packages.postBulk);
};

Gratipay.packages.initSingle = function() {
    Gratipay.Select('.gratipay-select');
    $('button.apply').on('click', Gratipay.packages.postOne);
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
        Gratipay.packages.post(email, package_ids_by_email[email], true);
};

Gratipay.packages.postOne = function(e) {
    e.preventDefault();
    var email = $('input[name=email]:checked').val();
    var package_id = $('input[name=package_id]').val();
    Gratipay.packages.post(email, [package_id]);
}


Gratipay.packages.post = function(email, package_ids, show_email) {
    var action = 'start-verification';
    var $button = $('button.apply')

    $button.prop('disabled', true);
    function reenable() { $button.prop('disabled', false); }
    $.ajax({
        url: '/~' + Gratipay.username + '/emails/modify.json',
        type: 'POST',
        data: { action: action
              , address: email
              , package_id: package_ids
              , show_address_in_message: true
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
