Gratipay.signIn = {};

Gratipay.signIn.wireUpButton = function() {
    $('.sign-in button').click(Gratipay.signIn.openSignInOrSignUpModal);
}

Gratipay.signIn.openSignInToContinueModal = function () {
    Gratipay.signIn.replaceTextInModal('sign-in-to-continue');
    Gratipay.modal.open('#sign-in-modal');
}

Gratipay.signIn.openSignInOrSignUpModal = function () {
    Gratipay.signIn.replaceTextInModal('sign-in-or-sign-up');
    Gratipay.modal.open('#sign-in-modal');
}

Gratipay.signIn.replaceTextInModal = function(dataKey) {
    $('#sign-in-modal').find('.sign-in-togglable').each(function () {
        var textToReplace = $(this).data(dataKey);
        $(this).text(textToReplace);
    });
}
