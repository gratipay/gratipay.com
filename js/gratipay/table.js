Gratipay.table = (function() {
    function init() {
        $('table[data-url]').each(initTable);
    }

    function initTable(i, table) {
        var dataUrl = $(table).data('url');
        jQuery.get(dataUrl).success(function(data) {
            $('.loading-indicator').remove();
            var rows = renderRows(data.members);
            $('tbody', table).html(rows);
        });
    }


    // Render Rows
    // ===========

    function renderRows(records) {
        nrecords = records.length;
        var rows = [];
        var checkmark = function() { $('<span>').html('&#x2713;')[0] };

        for (var i=0, len=records.length; i<len; i++) {
            var record = records[i];
            rows.push(Gratipay.jsonml(
                [ 'tr'
                , ['td', {'class': 'n'}, record.n]
                , ['td', ['a', {'href': '/'+record.username+'/'}, record.username]]
                , ['td', record.number === 'singular' ? '' : '✓']
                , ['td', record.giving === null ? '-' : record.giving]
                , ['td', record.receiving === null ? '-' : record.receiving]
                , ['td', record.goal > 0 ? record.goal : '-']
                , ['td', record.first_tagged]
                 ]
            ));
        }
        return rows;
    }


    // Export
    // ======

    return {init: init};
})();
