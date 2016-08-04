Gratipay.confirm = function(message, yes, no) {
    var $m = $('.modal');
    $m.show();
    $('.confirmation-message', $m).html(message);
    $('.yes', $m).click(function() { yes(); Gratipay.confirm.close(); });
    $('.no', $m).click(function() { no(); Gratipay.confirm.close(); });
};

Gratipay.confirm.close = function() {
    $('.modal').hide();
};
