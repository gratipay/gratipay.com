Gratipay.tabs = {}

Gratipay.tabs.init = function() {
    Gratipay.tabs.refresh()
    $('.tabs #tab-nav a').on('click', Gratipay.tabs.handleClick);
    $(window).bind('popstate', Gratipay.tabs.refresh);
}

Gratipay.tabs.refresh = function (e) {
    selectedTab = getQueryParam('tab') || $('.tab').first().data('tab');
    Gratipay.tabs.activateTab(selectedTab);
}

Gratipay.tabs.handleClick = function(e) {
    e.preventDefault();
    var $target = $(e.target);
    var selectedTab = $target.data('tab');
    history.pushState(null, null, "?tab=" + selectedTab);
    Gratipay.tabs.activateTab(selectedTab);
}

Gratipay.tabs.activateTab = function(tab) {
    $.each($('.tabs #tab-nav a'), function(i, obj) {
        var $obj = $(obj);
        if ($obj.data('tab') == tab) {
            $obj.addClass('selected');
        } else {
            $obj.removeClass('selected');
        }
    })

    $.each($('.tabs .tab'), function(i, obj) {
        var $obj = $(obj);
        if ($obj.data('tab') == tab) { $obj.show(); } else { $obj.hide(); }
    })
}

function getQueryParam(param)
{
    var query = window.location.search.substring(1);
    var vars = query.split('&');

    for (var i=0; i < vars.length; i++) {
        var pair = vars[i].split('=');
        if (pair[0] == param) {
            return pair[1];
        }
    }

    return(false);
}
