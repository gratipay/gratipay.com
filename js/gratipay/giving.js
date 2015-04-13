Gratipay.giving = {}

Gratipay.giving.init = function() {
    Gratipay.giving.activate_tab('active');
    $('.giving #tab-nav a').on('click', Gratipay.giving.handle_click);
}

Gratipay.giving.handle_click = function(e) {
    e.preventDefault();
    var $target = $(e.target);
    Gratipay.giving.activate_tab($target.data('tab'));
}

Gratipay.giving.activate_tab = function(tab) {
    $.each($('.giving #tab-nav a'), function(i, obj) {
        var $obj = $(obj);
        $obj.data('tab') == tab ? $obj.addClass('selected') : $obj.removeClass('selected');
    })

    $.each($('.giving .tab'), function(i, obj) {
        var $obj = $(obj);
        $obj.data('tab') == tab ? $obj.show() : $obj.hide();
    })
}

