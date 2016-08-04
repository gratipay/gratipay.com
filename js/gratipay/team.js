Gratipay.team = (function() {

    var $t = function(selector) { return selector ? $(selector, 'table.team') : $('table.team'); };

    function init() {
        $t('.lookup-container form').submit(add);
        $t('.lookup-results').on('click', 'li', selectLookupResult);
        $t('.query').focus().keyup(lookup);

        jQuery.get("index.json").success(function(d) {
            $('.loading-indicator').remove();
            drawRows(d.available, d.members);
        });
    }


    // Draw Rows
    // =========

    function num(n) { return n.toFixed(2); }
    function perc(n) { return (n * 100).toFixed(1); }

    function drawMemberTake(member) {
        var take = num(member.take);

        if (member.editing_allowed)
            return [ 'form'
                   , {'class': 'edit knob'}
                   , [ 'input'
                     , { 'value': take
                       , 'data-id': member.participant_id
                       , 'data-take': take // useful to reset form
                       , 'tabindex': '1'
                        }
                      ]
                    ];

        if (member.removal_allowed)
            return ['span', {'class': 'remove knob', 'data-id': member.participant_id}, take];

        return take;
    }

    function drawRows(available, members) {
        var nmembers = members.length;
        var rows = [];

        for (var i=0, len=members.length; i<len; i++) {
            var member = members[i];
            var increase = '';

            if (member.take > member.last_week)
                increase = 'moderate';
            if (member.take > (member.last_week * 1.25))
                increase = 'high';
            if (member.take === member.max_this_week)
                increase = 'max';

            rows.push(Gratipay.jsonml(
                [ 'tr'
                , ['td', {'class': 'n'}, (i === nmembers ? '' : nmembers - i)]
                , ['td', ['a', {'href': '/~'+member.username+'/'}, member.username]]
                , ['td', {'class': 'figure last_week'}, num(member.last_week)]
                , ['td', {'class': 'figure take ' + increase}, drawMemberTake(member)]
                , ['td', {'class': 'figure balance'}, num(member.balance)]
                , ['td', {'class': 'figure percentage'}, perc(member.percentage)]
                 ]
            ));
        }

        if (nmembers === 0) {
            rows.push(Gratipay.jsonml(
                ['tr', ['td', {'colspan': '6', 'class': 'no-members'}, "No members"]]
            ));
        } else {
            rows.push(Gratipay.jsonml(
                [ 'tr'
                , {'class': 'totals'}
                , ['td']
                , ['td']
                , ['td']
                , ['td', {'class': 'figure take'}, num(available - member.balance)]
                , ['td', {'class': 'figure balance'}, num(member.balance)]
                , ['td', {'class': 'figure percentage'}, perc(member.balance / available)]
                 ]
            ));
        }

        $t('.team-members').html(rows);
        $t('.team-members .edit').submit(doTake);
        $t('.team-members .edit input').focus().keyup(maybeCancelTake);
        $t('.team-members .remove').click(remove);
    }


    // Add
    // ===

    function lookup() {
        var query = $t('.query').val();
        if (query === '')
            $t('.lookup-results').empty();
        else
            jQuery.get("/lookup.json", {query: query}).success(drawLookupResults);
    }

    function drawLookupResults(results) {
        var items = [];
        for (var i=0, len=results.length; i<len; i++) {
            var result = results[i];
            items.push(Gratipay.jsonml(
                ['li', {"data-id": result.id}, result.username]
            ));
        }
        $t('.lookup-results').html(items);
        if (items.length === 1)
            selectLookupResult.call($t('.lookup-results li'));
    }

    function selectLookupResult() {
        $li = $(this);
        $t('.query').val($li.html()).data('id', $li.data('id'));
        $t('.lookup-results').empty();
    }

    function add(e) {
        e.preventDefault();
        e.stopPropagation();
        var participantId = $t('.query').data('id');
        setTake(participantId, '0.01');
        $t('.lookup-results').empty();
        $t('.query').val('').focus();
        return false;
    }

    function remove(e) {
        e.preventDefault();
        e.stopPropagation();
        var participantId = $(e.target).data('id');
        setTake(participantId, '0.00');
        return false;
    }


    // Take
    // ====

    function maybeCancelTake(e) {
        if (e.which === 27) {
            resetTake();
        }
    }

    function resetTake() {
        $t('.take .knob').show().parent().find('.updating').remove();
        var _ = $t('.take input');
        _.val(_.attr('data-take')).blur();
    }

    function doTake(e) {
        e.preventDefault();
        e.stopPropagation();
        var input = $t('.take input');
        var participantId = input.data('id'), take = input.val();
        setTake(participantId, take);
        return false;
    }

    function setTake(participantId, take, confirmed) {
        if ($t('.take').find('.updating').length === 0) {
            var $updating = $('<span class="updating"></span>');
            $updating.text($t().data('updating'));
            $t('.take .knob').hide().parent().append($updating);
        }

        var data = {take: take};
        if (confirmed) data.confirmed = true;

        jQuery.ajax(
                { type: 'POST'
                , url: participantId + ".json"
                , data: data
                , success: function(d) {
                    if (d.confirm) {
                        function proceed() { setTake(participantId, take, true); }
                        Gratipay.confirm(d.confirm, proceed, resetTake);
                    } else {
                        if(d.success) {
                            Gratipay.notification(d.success, 'success');
                        }
                        drawRows(d.available, d.members);
                    }
                }
                , error: [resetTake, Gratipay.error]
                 });
    }


    // Export
    // ======

    return {init: init};
})();
