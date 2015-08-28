/* Payment route forms
 *
 * These forms share some common wiring under the Gratipay.routes namespace,
 * and each has unique code under the Gratipay.routes.{cc,ba,pp} namespaces.
 * Each form gets its own page, so we only instantiate one of these at a time.
 *
 */

Gratipay.routes = {};


// Common code
// ===========

Gratipay.routes.init = function() {
    $('#delete').submit(Gratipay.routes.deleteRoute);
}

Gratipay.routes.lazyLoad = function(script_url) {
    jQuery.getScript(script_url, function() {
        $('input[type!="hidden"]').eq(0).focus();
    }).fail(Gratipay.error);
}

Gratipay.routes.redirectToOverview = function() {
    window.location = './';
};

Gratipay.routes.deleteRoute = function(e) {
    e.stopPropagation();
    e.preventDefault();

    var $this = $(this);
    var confirm_msg = $this.data('confirm');
    if (confirm_msg && !confirm(confirm_msg)) {
        return false;
    }
    jQuery.ajax(
        { url: "/~" + Gratipay.username + "/routes/delete.json"
        , data: {network: $this.data('network'), address: $this.data('address')}
        , type: "POST"
        , success: Gratipay.routes.redirectToOverview
        , error: Gratipay.error
         }
    );
    return false;
};

Gratipay.routes.onSuccess = function(data) {
    $('button#save').prop('disabled', false);
    Gratipay.routes.redirectToOverview();
};

Gratipay.routes.associate = function (network, address) {
    jQuery.ajax({
        url: "associate.json",
        type: "POST",
        data: {network: network, address: address},
        dataType: "json",
        success: Gratipay.routes.onSuccess,
        error: [
            Gratipay.error,
            function() { $('button#save').prop('disabled', false); },
        ],
    });
};


// Credit Cards
// ============

Gratipay.routes.cc = {};

Gratipay.routes.cc.init = function() {
    Gratipay.routes.init();

    // Lazily depend on Braintree.
    Gratipay.routes.lazyLoad("https://js.braintreegateway.com/v2/braintree.js")

    $('form#credit-card').submit(Gratipay.routes.cc.submit);
    Gratipay.routes.cc.formatInputs(
        $('#card_number'),
        $('#expiration_month'),
        $('#expiration_year'),
        $('#cvv')
    );
};


/* Most of the following code is taken from https://github.com/wangjohn/creditly */

Gratipay.routes.cc.formatInputs = function (cardNumberInput, expirationMonthInput, expirationYearInput, cvvInput) {
    function getInputValue(e, element) {
        var inputValue = element.val().trim();
        inputValue = inputValue + String.fromCharCode(e.which);
        return inputValue.replace(/[^\d]/g, "");
    }

    function isEscapedKeyStroke(e) {
        // Key event is for a browser shortcut
        if (e.metaKey || e.ctrlKey) return true;

        // If keycode is a space
        if (e.which === 32) return false;

        // If keycode is a special char (WebKit)
        if (e.which === 0) return true;

        // If char is a special char (Firefox)
        if (e.which < 33) return true;

        return false;
    }

    function isNumberEvent(e) {
        return (/^\d+$/.test(String.fromCharCode(e.which)));
    }

    function onlyAllowNumeric(e, maximumLength, element) {
        e.preventDefault();
        // Ensure that it is a number and stop the keypress
        if (!isNumberEvent(e)) {
            return false;
        }
        return true;
    }

    var isAmericanExpress = function(number) {
        return number.match("^(34|37)");
    };

    function shouldProcessInput(e, maximumLength, element) {
        var target = e.currentTarget;
        if (getInputValue(e, element).length > maximumLength) {
          e.preventDefault();
          return false;
        }
        if ((target.selectionStart !== target.value.length)) {
          return false;
        }
        return (!isEscapedKeyStroke(e)) && onlyAllowNumeric(e, maximumLength, element);
    }

    function addSpaces(number, spaces) {
      var parts = []
      var j = 0;
      for (var i=0; i<spaces.length; i++) {
        if (number.length > spaces[i]) {
          parts.push(number.slice(j, spaces[i]));
          j = spaces[i];
        } else {
          if (i < spaces.length) {
            parts.push(number.slice(j, spaces[i]));
          } else {
            parts.push(number.slice(j));
          }
          break;
        }
      }

      if (parts.length > 0) {
        return parts.join(" ");
      } else {
        return number;
      }
    }

    var americanExpressSpaces = [4, 10, 15];
    var defaultSpaces = [4, 8, 12, 16];

    cardNumberInput.on("keypress", function(e) {
        var number = getInputValue(e, cardNumberInput);
        var isAmericanExpressCard = isAmericanExpress(number);
        var maximumLength = (isAmericanExpressCard ? 15 : 16);
        if (shouldProcessInput(e, maximumLength, cardNumberInput)) {
            var newInput;
            newInput = isAmericanExpressCard ? addSpaces(number, americanExpressSpaces) : addSpaces(number, defaultSpaces);
            cardNumberInput.val(newInput);
        }
    });

    expirationMonthInput.on("keypress", function(e) {
        var maximumLength = 2;
        if (shouldProcessInput(e, maximumLength, expirationMonthInput)) {
            var newInput = getInputValue(e, expirationMonthInput);
            if (newInput < 13) {
                expirationMonthInput.val(newInput);
            } else {
                e.preventDefault();
            }
        }
    });

    expirationYearInput.on("keypress", function(e) {
        var maximumLength = 2;
        if (shouldProcessInput(e, maximumLength, expirationYearInput)) {
            var newInput = getInputValue(e, expirationYearInput);
            expirationYearInput.val(newInput);
        }
    });

    cvvInput.on("keypress", function(e) {
        var number = getInputValue(e, cardNumberInput);
        var isAmericanExpressCard = isAmericanExpress(number);
        var maximumLength = (isAmericanExpressCard ? 4 : 3);
        if (shouldProcessInput(e, maximumLength, cvvInput)) {
            var newInput = getInputValue(e, cvvInput);
            cvvInput.val(newInput);
        }
    });
}

Gratipay.routes.cc.submit = function(e) {

    e.stopPropagation();
    e.preventDefault();
    $('button#save').prop('disabled', true);
    Gratipay.forms.clearInvalid($(this));

    // Adapt our form lingo to braintree nomenclature.

    function val(field) {
        return $('form#credit-card #'+field).val();
    }

    var credit_card = {};

    credit_card.number = val('card_number').replace(/[^\d]/g, '');
    credit_card.cvv = val('cvv');
    credit_card.cardholderName = val('name');
    credit_card.billingAddress = { 'postalCode': val('zip') };
    credit_card.expirationMonth = val('expiration_month');
    var year = val('expiration_year');
    credit_card.expirationYear = year.length == 2 ? '20' + year : year;

    // TODO: Client Side validation

    var client = new braintree.api.Client({clientToken: val('braintree_token')});

    client.tokenizeCard(credit_card, function (err, nonce) {
        if (err) {
            Gratipay.notification(err, 'error')
        } else {
            Gratipay.routes.associate('braintree-cc', nonce);
        }
    });

    return false;
};


// PayPal
// ======

Gratipay.routes.pp = {};

Gratipay.routes.pp.init = function () {
    Gratipay.routes.init();
    $('form#paypal').submit(Gratipay.routes.pp.submit);
}

Gratipay.routes.pp.submit = function (e) {
    e.stopPropagation();
    e.preventDefault();
    $('button#save').prop('disabled', true);
    var paypal_email = $('form#paypal #email').val();

    Gratipay.routes.associate('paypal', paypal_email);
}
