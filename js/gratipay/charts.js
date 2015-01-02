Gratipay.charts = {};


Gratipay.charts.make = function(series) {
    // Takes an array of time series data.

    if (!series.length) {
        $('.chart-wrapper').remove();
        return;
    }


    // Sort the series in increasing date order.
    // =========================================

    series.sort(function(a,b) { return a.date > b.date ? 1 : -1 });


    // Gather charts.
    // ==============
    // Sniff the first element to determine what data points are available, and
    // then search the page for chart containers matching each data point
    // variable name.

    var point  = series[0];
    var charts = [];

    for (var varname in point) {
        var chart = $('#chart_'+varname);
        if (chart.length) {
            chart.varname = varname;
            charts.push(chart);
        }
    }

    var H = $('.chart').height();
    var nweeks = series.length;
    var w = (1 / nweeks * 100).toFixed(10) + '%';

    $('.n-weeks').text(nweeks);


    // Compute maxes and scales.
    // =========================

    var maxes  = [];
    var scales = [];

    for (var i=0, point; point = series[i]; i++) {
        for (var j=0, chart; chart = charts[j]; j++) {
            maxes[j] = Math.max(maxes[j] || 0, point[chart.varname]);
        }
    }

    for (var i=0, len=maxes.length; i < len; i++) {
        var max = parseInt(charts[i].attr('data-y-max') || maxes[i], 10);
        scales.push(Math.ceil(max / 100) * 100);
    }


    // Draw weeks.
    // ===========

    function Week(i, j, N, y, title) {
        var week   = $(document.createElement('div')).addClass('week');
        var shaded = $(document.createElement('div')).addClass('shaded');
        shaded.html('<span class="y-label">'+ y.toFixed() +'</span>');
        week.append(shaded);

        var xTick = $(document.createElement('span')).addClass('x-tick');
        xTick.text(i).attr('title', title);
        week.append(xTick);

        if (y > scales[j]) {
            // clip with no flag
            y = scales[j];
        }

        // Display a max flag (only once)
        if (y === maxes[j]) {
            maxes[j] = undefined;
            week.addClass('flagged');
        }

        week.css('width', w);
        shaded.css('height', y / N * H);
        return week;
    }

    function wireup(week) {
        week.click(function() {
            $(this).toggleClass('flagged');
            if ($(this).hasClass('flagged'))
                $(this).removeClass('hover');
        });

        week.mouseover(function() {
            $(this).addClass('hover');
        });

        week.mouseout(function() {
            $(this).removeClass('hover');
        });
    }

    for (var i=0, point; point = series[i]; i++) {
        for (var j=0, chart; chart = charts[j]; j++) {
            var week = Week(i, j, scales[j], point[chart.varname], point.date);
            wireup(week);
            chart.append(week);
        }
    }

};


Gratipay.charts.retention = {};


Gratipay.charts.retention.make = function(data) {

    Gratipay.charts.make(data[0]);  // new_users

    var retention = data[1];
    var nweeks = retention.length;
    var w = (1 / nweeks * 100).toFixed(10) + '%';
    var chart = $('#chart_retention');

    function get_color(p) {
        return 'hsl(149,50%,' + (100 - (p*60)).toFixed() + '%)';
    }

    for (var i=0; i < nweeks; i++) {
        var nretention = retention[i].length;
        var week = $(document.createElement('div')).addClass('week').css('width', w);
        for (var j=0; j < nretention; j++) {
            var retained = $(document.createElement('div')).addClass('retained');
            var p = parseFloat(retention[i][j][0], 10);
            retained.css({background: get_color(p), height: '1'});
            week.append(retained);
        }
        chart.append(week);
    }
};
