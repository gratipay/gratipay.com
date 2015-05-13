Gratipay.new_team = {}

Gratipay.new_team.initForm = function () {
    $form = $('#new-team');
    $button = $form.find('button');
    $button.on('click', Gratipay.new_team.submitForm);
}

Gratipay.new_team.submitForm = function (e) {
    e.preventDefault();

    $input = $(this)
    $form = $(this).parent('form');
    var data = $form.serializeArray();

    $input.prop('disable', true);

    $.ajax({
        url: $form.attr('action'),
        type: 'POST',
        data: data,
        dataType: 'json',
        success: function (d) {
            $('form').html( "<p>Thank you! We will follow up shortly with an email to <b>"
                          + d.email + "</b>. Please <a hef=\"mailto:support@gratipay.com\">email "
                          + "us</a> with any questions.</p>"
                           )
        },
        error: [Gratipay.error, function () { $input.prop('disable', false); }]
    });
}
