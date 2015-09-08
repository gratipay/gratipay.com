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
            $('a.review_url').attr('href', d.review_url).text(d.review_url);
            $('form').slideUp(500, function() {
                $('.application-complete').slideDown(250);
            });
        },
        error: [Gratipay.error, function () { $input.prop('disable', false); }]
    });
}
