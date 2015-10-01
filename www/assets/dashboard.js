var ENTER_KEY = 13;
var ESCAPE_KEY = 27;

Dashboard = {models: {}, views: {}, collections: {}};

Dashboard.Router = Backbone.Router.extend({
    routes: {'ledger': 'ledger', 'accounts': 'accounts'},
    ledger: function() {
        $('section').hide();
        $('#navigation a.selected').removeClass('selected');
        $('#navigation a[href=ledger]').addClass('selected');
        $('#general-ledger').show();
    },
    accounts: function() {
        $('section').hide();
        $('#navigation a.selected').removeClass('selected');
        $('#navigation a[href=accounts]').addClass('selected');
        $('#chart-of-accounts').show();
    }
});


// Models
// ======

Dashboard.models.Account = Backbone.Model.extend({
    idAttribute: 'number',
    defaults: {
        number: null,
        name: null,
    }
});


// Collections
// ===========

Dashboard.collections.Accounts = Backbone.Collection.extend({
    url: '/api/v2/accounts/',
    model: Dashboard.models.Account,
});


// Views
// =====

Dashboard.views.Main = Backbone.View.extend({
    el: 'body',
    initialize: function() {
        new Dashboard.views.GeneralLedger;
        new Dashboard.views.ChartOfAccounts;

        this.router = new Dashboard.Router;
        Backbone.history.start({pushState: true, root: "/dashboard/"});
    },
    events: {
        'click #navigation a': 'loadSection'
    },
    loadSection: function(e) {
        this.router.navigate($(e.currentTarget).attr('href'), {trigger: true});
        e.preventDefault();
    },
});

Dashboard.views.GeneralLedger = Backbone.View.extend({
    el: '#general-ledger',
    initialize: function() {
    },
});

Dashboard.views.ChartOfAccounts = Backbone.View.extend({
    el: '#chart-of-accounts',
    initialize: function() {
        this.collection = new Dashboard.collections.Accounts();
        new Dashboard.views.AccountsListing({collection: this.collection});
        new Dashboard.views.AddAccount({collection: this.collection});
    },
});


Dashboard.views.AccountsListing = Backbone.View.extend({
    el: '#chart-of-accounts tbody',
    initialize: function() {
        this.listenTo(this.collection, 'reset', this.render);
        this.listenTo(this.collection, 'sync', this.render);
        this.collection.fetch({reset:true});
    },
    render: function() {
        this.$el.html('');
        this.collection.each(this.addOne, this);
        return this;
    },
    addOne: function(account) {
        var view = new Dashboard.views.AccountRow({model: account});
        var el = view.render().el;
        this.$el.append(el);
    },
});

Dashboard.views.AccountRow = Backbone.View.extend({
    tagName: 'tr',
    initialize: function() {
        this.template = _.template($('#AccountRow').html());
        this.listenTo(this.model, 'change', this.render);
    },
    render: function() {
        this.$el.html(this.template(this.model.attributes));
        return this;
    },
    events: {
        'dblclick td': 'turnEditAccountOn',
        'keydown input' : 'keyAction'
    },
    turnEditAccountOn: function(e) {
        this.$el.addClass('editing');
        this.$('.view').hide();
        this.$('.edit').show();
        $('input', e.currentTarget).focus();
    },
    turnEditAccountOff: function() {
        this.$el.removeClass('editing');
        this.$('.view').show();
        this.$('.edit').hide();
    },
    keyAction: function(e) {
        switch (e.which) {
            case (ENTER_KEY):
                this.editAccount();
                break;
            case (ESCAPE_KEY):
                this.turnEditAccountOff();
                break;
        }
    },
    editAccount: function() {
        var data = { number: $.trim(this.$('input[name=number]').val())
                   , name: $.trim(this.$('input[name=name]').val())
                    };
        if (data.number && data.name) {
            this.model.save(data, {wait: true});
        }
    }
});




Dashboard.views.AddAccount = Backbone.View.extend({
    el: '#chart-of-accounts tfoot',
    initialize: function() {
        this.$el.html($('#AddAccount').html());
        this.turnAddAccountOff();
    },
    events: {
        'click .off button': 'turnAddAccountOn',
        'click .on button[type=cancel]': 'turnAddAccountOff',
        'click button[type=submit]': 'addAccount',
        'keydown input' : 'keyAction'
    },
    turnAddAccountOn: function() {
        this.$('.off').hide();
        this.$('.on').show();
        this.$('.on input').first().focus();
    },
    turnAddAccountOff: function() {
        this.$('.on').hide();
        this.$('.off').show();
    },
    keyAction: function(e) {
        if (e.which === ENTER_KEY)
            this.addAccount();
    },
    addAccount: function() {
        var data = { number: $.trim(this.$('input[name=number]').val())
                   , name: $.trim(this.$('input[name=name]').val())
                    };
        if (data.number && data.name) {
            function success() {
                this.$('input').val('').first().focus();
            }
            this.collection.create(data, {success: success, wait: true});
        }
    }
});


// CSRF
// ====
// WET - see js/gratipay/forms.js
//
Dashboard.getCookie = function(key) {
    var o = new RegExp("(?:^|; ?)" + escape(key) + "=([^;]+)").exec(document.cookie);
    return o && unescape(o[1]);
}

Dashboard.initCSRF = function() {
    jQuery(document).ajaxSend(function(event, xhr, settings) {
        function sameOrigin(url) {
            // url could be relative or scheme relative or absolute
            var host = document.location.host; // host + port
            var protocol = document.location.protocol;
            var sr_origin = '//' + host;
            var origin = protocol + sr_origin;
            // Allow absolute or scheme relative URLs to same origin
            return (url == origin || url.slice(0, origin.length + 1) == origin + '/') ||
                (url == sr_origin || url.slice(0, sr_origin.length + 1) == sr_origin + '/') ||
                // or any other URL that isn't scheme relative or absolute i.e relative.
                !(/^(\/\/|http:|https:).*/.test(url));
        }
        function safeMethod(method) {
            return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
        }

        if (!safeMethod(settings.type) && sameOrigin(settings.url)) {
            // We have to avoid httponly on the csrf_token cookie because of this.
            // https://github.com/gratipay/gratipay.com/issues/3030
            xhr.setRequestHeader("X-CSRF-TOKEN", Dashboard.getCookie('csrf_token'));
        }
    });
};


// Entrypoint
// ==========

Dashboard.init = function() {
    new Dashboard.views.Main();
    Dashboard.initCSRF();
};
