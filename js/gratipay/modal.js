Gratipay.modal = {}

Gratipay.modal.open = function(modalWrapper) {
    $('body').append('<div id="modal-grayout"></div>');
    $(modalWrapper).show().focus();

    var closeModal = function() {
        Gratipay.modal.close(modalWrapper);
    };
    $('#modal-grayout').click(closeModal);
    $(modalWrapper).find('button.close-modal').click(closeModal);
};

Gratipay.modal.close = function(modalWrapper) {
    $(modalWrapper).hide();
    $('#modal-grayout').remove();
};
