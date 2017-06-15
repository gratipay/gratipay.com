$(document).ready(function()
{
    Gratipay.forms.initCSRF();

    function error(a,b,c)
    {
        console.log(a,b,c);
        alert("Failed!");
    }

    $('button').click(function()
    {
        var row = $(this).parent().parent();
        var to = $(this).text() !== 'Good';
        var username = row.data('username');
        var url = "/~" + username + "/toggle-is-suspicious.json";

        function success()
        {
            row.remove();
            $('iframe').attr('src', '');
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

