/**
 * Display a notification
 * Valid notification types are: "notice", "error", and "success".
 */
Gratipay.notification = function(text, type, timeout, closeCallback) {
    var type = type || 'notice';
    var timeout = timeout || (type == 'error' ? 10000 : 5000);
    var id = Math.random().toString(36).substring(2, 100);

    // We want the notification to be fixed at the top of the page even while
    // scrolling, without interfering with the heading that's already at the
    // top of the page when scrolled the whole way up (logo, sign in, etc.). So
    // what we do is create two notification divs. One sits behind and pushes
    // the rest of the page content down, so that the header remains visible.
    // The other sits in front, and is the one the user actually interacts
    // with. It stays at the top of the viewport even while scrolling.

    var placeholder = ['div', {'class': 'notification notification-' + type}, ['div', text]];
    var dialog = ['div', {'class': 'notification notification-' + type, 'id': 'notification-'+id},
                                                                                    ['div', text]];
    var $dialog = $([
        Gratipay.jsonml(placeholder),   // pushes the whole page down, but not directly seen
        Gratipay.jsonml(dialog)         // parked at the top even while scrolling
    ]);

    // Close if we're on the page the notification links to.
    var links = $dialog.eq(1).find('a');
    if (links.length == 1 && links[0].pathname == location.pathname) {
        return closeCallback()
    }

    if (!$('#notification-area').length)
        $('body').prepend('<div id="notification-area"><div class="notifications-fixed"></div></div>');

    $('#notification-area').prepend($dialog.get(0));
    $('#notification-area .notifications-fixed').prepend($dialog.get(1));

    function close() {
        $dialog.fadeOut(null, function() { $dialog.remove(); delete $dialog; });
        if (closeCallback) closeCallback();
    }

    $dialog.append($('<span class="btn-close">&times;</span>').click(close));
    if (timeout > 0) setTimeout(close, timeout);
};

Gratipay.notification.clear = function() {
    $('.notification').hide();
};

Gratipay.initNotifications = function(notifs) {
    jQuery.each(notifs, function(k, notif) {
        Gratipay.notification(notif.jsonml, notif.type, -1, function() {
            jQuery.ajax({
                url: '/~'+Gratipay.username+'/notifications.json',
                type: 'POST',
                data: {remove: notif.name},
                dataType: 'json',
                error: Gratipay.error,
            });
        });
    });
};
