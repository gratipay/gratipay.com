Gratipay.edit_team = {}

Gratipay.edit_team.initForm = function() {
    $form = $("#edit-team");
    $buttons = $form.find("button"); // submit and cancel btns
    $form.submit(Gratipay.edit_team.submitForm);
}

Gratipay.edit_team.submitForm = function(e) {
    e.preventDefault();

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