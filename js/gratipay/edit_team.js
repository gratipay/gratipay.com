Gratipay.edit_team = {}

Gratipay.edit_team.initForm = function() {
    $form = $("#edit-team");

    $form.find(":input").each(function() {
        // Save original values.
        $(this).data('original', $(this).val());
    });
    $form.submit(Gratipay.edit_team.submitForm);
}

Gratipay.edit_team.submitForm = function(e) {
    e.preventDefault();

    var modified = false;

    var data = new FormData();
    $form.find(":input").each(function() {
        if($(this).data("original") !== $(this).val()) {
            modified = true;

            var name = $(this).attr("name");
            if (name === "image") {
                data.append(name, $(this)[0].files[0]);
            } else {
                data.append(name, $(this).val());
            }
        }
    });

    if(modified) {
        $.ajax({
            url: $form.attr("action"),
            type: $form.attr("method"),
            data: data,
            dataType: 'json',
            processData: false,
            contentType: false,
            success: function(d) {
                Gratipay.notification("Successfully edited team.", 'success');
                setTimeout(function() { window.location.reload(); }, 1000);
            },
            error: Gratipay.error
        });
    }
}