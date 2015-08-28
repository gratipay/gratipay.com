$(document).ready(function() {
    $('.jump-box').submit(function (e) {
        e.preventDefault();
        e.stopPropagation();

        var platform = Gratipay.trim($('.jump-box select').val()),
            val      = Gratipay.trim($('.jump-box input').val());
        if (val) window.location = '/on/' + platform + '/' + val + '/';
    });
});
