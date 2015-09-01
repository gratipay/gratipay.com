Gratipay.tabs = {}

Gratipay.tabs.init = function() {
    var firstTab = $('.tab').first().data('tab');
    Gratipay.tabs.activateTab(firstTab);
    $('.tabs #tab-nav a').on('click', Gratipay.tabs.handleClick);
}

Gratipay.tabs.handleClick = function(e) {
    e.preventDefault();
    var $target = $(e.target);
    Gratipay.tabs.activateTab($target.data('tab'));
}

Gratipay.tabs.activateTab = function(tab) {
    $.each($('.tabs #tab-nav a'), function(i, obj) {
        var $obj = $(obj);
        if ($obj.data('tab') == tab) {
            $obj.addClass('selected');
        } else {
            $obj.removeClass('selected');
        }
    })

    $.each($('.tabs .tab'), function(i, obj) {
        var $obj = $(obj);
        if ($obj.data('tab') == tab) { $obj.show(); } else { $obj.hide(); }
    })
}
