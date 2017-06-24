Gratipay.countryChooser = {}

Gratipay.countryChooser.init = function() {
    $('.open-country-chooser').click(Gratipay.countryChooser.open);
};

Gratipay.countryChooser.open = function() {
    Gratipay.modal.open('#country-chooser');
};
