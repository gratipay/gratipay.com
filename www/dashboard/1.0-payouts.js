$(document).ready(function()
{
    Gratipay.forms.initCSRF();

    function loadNext() {
        var next = $('.unreviewed a').attr('href') || '1.0-payouts-done.html';
        $('iframe').attr('src', next);
    };

    function error(a,b,c)
    {
        console.log(a,b,c);
        alert("Failed!");
    }

    loadNext();
    $('button').click(function()
    {
        var button = $(this);
        var row = $(this).parent();
        var to = $(this).text() === 'Good' ? 'pending-payout' : 'rejected';
        var username = row.attr('username');
        var url = "/~" + username + "/payout-status";

        function success(d)
        {
            button.blur();
            row.removeClass('unreviewed');
            loadNext();
            row.addClass(d.status == 'pending-payout' ? 'good' : 'bad');
        }

        jQuery.ajax({ url: url
                    , type: "POST"
                    , dataType: "json"
                    , data: {to: to}
                    , success: success
                    , error: error
                     })
    });
});
