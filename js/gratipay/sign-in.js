Gratipay.signIn = {};

Gratipay.signIn.wireUp = function() {
    Gratipay.signIn.wireUpButton();
    Gratipay.signIn.wireUpEmailInput();
}

Gratipay.signIn.wireUpButton = function() {
    $('.sign-in button').click(Gratipay.signIn.openSignInOrSignUpModal);
}

Gratipay.signIn.wireUpEmailInput = function() {
    $('#sign-in-modal form.email-form').submit(function(e) {
        e.preventDefault();
        jQuery.ajax({
            url: '/auth/send-link.json',
            type: 'POST',
            data: {
                'email_address': $(this).find('input').val()
            },
            success: function(data) {
                Gratipay.notification(data.message, 'success');
            },
            error: Gratipay.error
        });
    });
}

Gratipay.signIn.openSignInToContinueModal = function() {
    Gratipay.signIn.replaceTextInModal('sign-in-to-continue');
    Gratipay.signIn.openModalAndFocusInput();
}

Gratipay.signIn.openSignInOrSignUpModal = function() {
    Gratipay.signIn.replaceTextInModal('sign-in-or-sign-up');
    Gratipay.signIn.openModalAndFocusInput();
}

Gratipay.signIn.replaceTextInModal = function(dataKey) {
    $('#sign-in-modal').find('.sign-in-togglable').each(function () {
        var textToReplace = $(this).data(dataKey);
        $(this).text(textToReplace);
    });
}

Gratipay.signIn.openModalAndFocusInput = function() {
    Gratipay.modal.open('#sign-in-modal');
    $('#sign-in-modal input').focus();
}
