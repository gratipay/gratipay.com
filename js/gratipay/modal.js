Gratipay.modal = {}

Gratipay.modal.open = function(modalWrapper) {
    $(modalWrapper).show().focus();

    var closeModal = function() {
        Gratipay.modal.close(modalWrapper);
    };
    $(modalWrapper).on('click', function (e) {
        if (e.target === this) {
            closeModal();
        } else {
            return; // Don't close modal if the click was on descendants
        }
    });
    $(modalWrapper).find('button.close-modal').click(closeModal);
};

Gratipay.modal.close = function(modalWrapper) {
    $(modalWrapper).hide();
};
