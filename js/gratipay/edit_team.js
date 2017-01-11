Gratipay.edit_team = {}

Gratipay.edit_team.initForm = function() {
    $('#edit-team').submit(Gratipay.edit_team.submitForm);
    $('#close-team').submit(function() { return confirm('Really close project?') });
}

Gratipay.edit_team.submitForm = function(e) {
    e.preventDefault();

    var $form = $("#edit-team");
    var $buttons = $form.find("button");
    var data = new FormData($form[0]);

    $buttons.prop("disabled", true);
    $.ajax({
        url: $form.attr("action"),
        type: $form.attr("method"),
        data: data,
        dataType: 'json',
        processData: false,
        contentType: false,
        success: function(d) {
            Gratipay.notification("Successfully edited team.", 'success');
            setTimeout(function() {
                window.location.href = "../";
            }, 1000);
        },
        error: [Gratipay.error, function () { $buttons.prop("disabled", false); }]
    });
}
