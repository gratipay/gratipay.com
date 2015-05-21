Gratipay.subscriptions = {}

Gratipay.subscriptions.init = function() {
    Gratipay.subscriptions.activateTab('active');
    $('.subscriptions #tab-nav a').on('click', Gratipay.subscriptions.handleClick);
}

Gratipay.subscriptions.handleClick = function(e) {
    e.preventDefault();
    var $target = $(e.target);
    Gratipay.subscriptions.activateTab($target.data('tab'));
}

Gratipay.subscriptions.activateTab = function(tab) {
    $.each($('.subscriptions #tab-nav a'), function(i, obj) {
        var $obj = $(obj);
        if ($obj.data('tab') == tab) {
            $obj.addClass('selected');
        } else {
            $obj.removeClass('selected');
        }
    })

    $.each($('.subscriptions .tab'), function(i, obj) {
        var $obj = $(obj);
        if ($obj.data('tab') == tab) { $obj.show(); } else { $obj.hide(); }
    })
}

