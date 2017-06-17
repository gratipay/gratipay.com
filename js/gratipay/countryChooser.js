Gratipay.countryChooser = {}

Gratipay.countryChooser.init = function() {
    $('.open-country-chooser').click(Gratipay.countryChooser.open);
    $('.close-country-chooser').click(Gratipay.countryChooser.close);
};

Gratipay.countryChooser.open = function() {
    $('.open-country-chooser').blur();
    $('body').append('<div id="modal-grayout"></div>');
    $('#modal-grayout').click(Gratipay.countryChooser.close);
    $('#country-chooser').show();
};

Gratipay.countryChooser.close = function() {
    $('#country-chooser').hide();
    $('#modal-grayout').remove();
};
