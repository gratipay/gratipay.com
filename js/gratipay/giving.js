Gratipay.giving = {}

Gratipay.giving.init = function() {
    Gratipay.giving.activateTab('active');
    $('.giving #tab-nav a').on('click', Gratipay.giving.handleClick);
}

Gratipay.giving.handleClick = function(e) {
    e.preventDefault();
    var $target = $(e.target);
    Gratipay.giving.activateTab($target.data('tab'));
}

Gratipay.giving.activateTab = function(tab) {
    $.each($('.giving #tab-nav a'), function(i, obj) {
        var $obj = $(obj);
        if ($obj.data('tab') == tab) {
            $obj.addClass('selected');
        } else {
            $obj.removeClass('selected');
        }
    })

    $.each($('.giving .tab'), function(i, obj) {
        var $obj = $(obj);
        if ($obj.data('tab') == tab) { $obj.show(); } else { $obj.hide(); }
    })
}

