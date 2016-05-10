Gratipay.countryChooser = {}

Gratipay.countryChooser.init = function() {
    $('.open-country-chooser').click(Gratipay.countryChooser.open);
    $('.close-country-chooser').click(Gratipay.countryChooser.close);
    $('#grayout').click(Gratipay.countryChooser.close);
};

Gratipay.countryChooser.open = function() {
    $('.open-country-chooser').blur();
    $('#grayout').show()
    $('#country-chooser').show();
};

Gratipay.countryChooser.close = function() {
    $('#country-chooser').hide()
    $('#grayout').hide()
};
