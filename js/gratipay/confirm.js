Gratipay.confirm = function(message, yes, no) {
    var $m = $('.confirmation-modal');
    $m.show();
    $('.confirmation-message', $m).html(message);
    $('.yes', $m).off('click').click(function() { yes(); Gratipay.confirm.close(); });
    $('.no', $m).off('click').click(function() { no(); Gratipay.confirm.close(); });
};

Gratipay.confirm.close = function() {
    $('.confirmation-modal').hide();
};
