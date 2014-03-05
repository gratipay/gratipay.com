Gittip.tips = {};

Gittip.tips.init = function() {

    // Check the tip value on change, or 0.7 seconds after the user stops typing.
    // If the user presses enter, the browser should natively submit the form.
    // If the user presses cancel, we reset the form to its previous state.
    var timer;
    $('input.my-tip').change(checkTip).keyup(function(e) {
        if (e.keyCode === 27)                          // escape
            $(this).parents('form').trigger('reset');
        else if (e.keyCode === 38 || e.keyCode === 40) // up & down
            return; // causes inc/decrement in HTML5, triggering the change event
        else {
            clearTimeout(timer);
            timer = setTimeout(checkTip.bind(this), 700);
        }
    });

    function checkTip() {
        var $this     = $(this),
            $parent   = $this.parents('form'),
            $confirm  = $parent.find('.confirm-tip'),
            amount    = parseFloat($this.val(), 10) || 0,
            oldAmount = parseFloat(this.defaultValue, 10),
            max       = parseFloat($this.prop('max')),
            min       = parseFloat($this.prop('min')),
            inBounds  = amount <= max && amount >= min,
            same      = amount === oldAmount;

        // dis/enables confirm button as needed
        $confirm.prop('disabled', inBounds ? same : true);

        if (same)
            $parent.removeClass('changed');
        else
            $parent.addClass('changed');

        // show/hide the payment prompt
        if (amount)
            $('#payment-prompt').addClass('needed');
        else
            $('#payment-prompt').removeClass('needed');
    }

    $('.my-tip .cancel-tip').click(function(event) {
        event.preventDefault();

        $(this).parents('form').trigger('reset');
    });

    $('.my-tip .tip-suggestions a').click(function(event) {
        event.preventDefault();

        var $this  = $(this),
            $myTip = $this.parents('form').find('.my-tip');

        var amount = $this.text().match(/\d+.\d+/);
        $myTip.val(amount).change();

    });

    $('form.my-tip').on('reset', function() {
        $(this).removeClass('changed');
        $(this).find('.confirm-tip').prop('disabled', true);
    });

    $('form.my-tip').submit(function(event) {
        event.preventDefault();

        var $this     = $(this),
            $myTip    = $this.find('.my-tip'),
            amount    = parseFloat($myTip.val(), 10),
            oldAmount = parseFloat($myTip[0].defaultValue, 10),
            tippee    = $myTip.data('tippee'),
            isAnon    = $this.hasClass('anon');

        if (amount == oldAmount)
            return;

        if(isAnon) {
            alert("Please sign in first");
        }
        else {
            // send request to change tip
            $.post('/' + tippee + '/tip.json', { amount: amount }, function(data) {
                // lock-in changes
                $myTip[0].defaultValue = amount;
                $myTip.change();

                // update display
                $('.my-total-giving').text('$'+data.total_giving);
                $('.total-receiving').text(
                    // check and see if we are on our giving page or not
                    new RegExp('/' + tippee + '/').test(window.location.href) ?
                        '$'+data.total_receiving_tippee : '$'+data.total_receiving);

                // Increment an elsewhere receiver's "people ready to give"
                if(!oldAmount)
                    $('.on-elsewhere .ready .number').text(
                        parseInt($('.on-elsewhere .ready .number').text(),10) + 1);
                
                // show payment method dialog
                if (has_payment_method === "False") {
                    $('#payment-method-dialog').show();
                    $("#payment-method").css({
                        "marginLeft": -($("#payment-method").width()/2),
                        "marginTop": -($("#payment-method").height()/2)
                    });
                }

                // update quick stats
                $('.quick-stats a').text('$' + data.total_giving + '/wk');

                // show confirmation message once
                if ($(".confirm").length > 0){
                    $(".confirm").remove();
                }
                var notice = $('<div class="confirm">Your weekly gift has been updated.</div>');
                $('#hero').prepend(notice);
            
                // update amount
                $('.weekly-gift .amount').text('$' + $('input.my-tip').val() + ' / wk');
            })
            .fail(function() {
                alert('Sorry, something went wrong while changing your tip. :(');
                console.log.apply(console, arguments);
            })
        }
    });

    // highlight radio selection    
    $paymentOption = $('#payment-method input:radio[name=payment-option]');
    $paymentOption.click(function(e) {
        $paymentOption.each(function (index, item){
            if($(item).is(":checked")){
                $(item).parent().addClass('selected');
            } else {
                $(item).parent().removeClass('selected');
            }        
        });
    });

    // connect to coinbase
    $('.promo-bar a.coinbase').click(function(e) {
        e.preventDefault();
        Gittip.payments.cb.init(marketplace_uri, participant_username);
    });

    // payment method selection
    $('#payment-method .primary').click(function(e) {
        e.preventDefault();

        if($('input:radio[name=payment-option]:checked').val() == 'coinbase') {
            Gittip.payments.cb.init(marketplace_uri, participant_username);
            $('#payment-method-dialog').hide();
        } else {
            window.location.href="/credit-card.html"
        }
    });

    // close payment method dialog
    $('#payment-method .close, #payment-method .secondary, #payment-method-dialog .overlay').click(function(e) {
        $('#payment-method-dialog').hide();
    });
};

