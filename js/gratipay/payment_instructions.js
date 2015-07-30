Gratipay.payment_instructions = {}

Gratipay.payment_instructions.init = function() {
    Gratipay.payment_instructions.activateTab('active');
    $('.payment_instructions #tab-nav a').on('click', Gratipay.payment_instructions.handleClick);
}

Gratipay.payment_instructions.handleClick = function(e) {
    e.preventDefault();
    var $target = $(e.target);
    Gratipay.payment_instructions.activateTab($target.data('tab'));
}

Gratipay.payment_instructions.activateTab = function(tab) {
    $.each($('.payment_instructions #tab-nav a'), function(i, obj) {
        var $obj = $(obj);
        if ($obj.data('tab') == tab) {
            $obj.addClass('selected');
        } else {
            $obj.removeClass('selected');
        }
    })

    $.each($('.payment_instructions .tab'), function(i, obj) {
        var $obj = $(obj);
        if ($obj.data('tab') == tab) { $obj.show(); } else { $obj.hide(); }
    })
}

