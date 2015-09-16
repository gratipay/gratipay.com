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
    defaults: {
        number: null,
        name: null,
        type: null
    }
});


// Collections
// ===========

Dashboard.collections.Accounts = Backbone.Collection.extend({
    url: '/v2/accounts/',
    model: Dashboard.models.Account,
    parse: function(data) {
        return data.accounts;
    }
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
        this.$tbody= this.$('tbody');
    },
});

Dashboard.views.ChartOfAccounts = Backbone.View.extend({
    el: '#chart-of-accounts',
    initialize: function() {
        this.$table = this.$('table');
        this.$tbody = this.$('tbody');
        this.data = new Dashboard.collections.Accounts();
        this.listenTo(this.data, 'reset', this.addAll);
        this.data.fetch({reset:true});

        this.addAccountOff = new Dashboard.views.AddAccountOff;
        this.addAccountOn = new Dashboard.views.AddAccountOn;

        this.turnAddAccountOff();
    },
    addOne: function (account) {
        var view = new Dashboard.views.AccountRow({model: account});
        var el = view.render().el;
        this.$tbody.append(el);
    },
    addAll: function () {
        this.$tbody.html('');
        this.data.each(this.addOne, this);
    },
    events: {
        'click .add-account.off button': 'turnAddAccountOn',
        'click .add-account.on button[type=cancel]': 'turnAddAccountOff',
        'click .add-account.on button[type=submit]': 'addAccount'
    },
    turnAddAccountOn: function() {
        this.addAccountOff.remove();
        this.$table.append(this.addAccountOn.render().el);
    },
    turnAddAccountOff: function() {
        this.addAccountOn.remove();
        this.$table.append(this.addAccountOff.render().el);
    },
    addAccount: function() {
        console.log('adding account ...');
    }
});

Dashboard.views.AccountRow = Backbone.View.extend({
    tagName: 'tr',
    initialize: function() {
        this.template = _.template($('#AccountRow').html());
    },
    render: function() {
        this.$el.html(this.template(this.model.toJSON()));
        return this;
    }
});

Dashboard.views.AddAccountOff = Backbone.View.extend({
    tagName: 'tfoot',
    className: 'add-account off',
    initialize: function() {
        this.template = _.template($('#AddAccountOff').html());
    },
    render: function() {
        this.$el.html(this.template());
        return this;
    },
});

Dashboard.views.AddAccountOn = Backbone.View.extend({
    tagName: 'tfoot',
    className: 'add-account on',
    initialize: function() {
        this.template = _.template($('#AddAccountOn').html());
    },
    render: function() {
        this.$el.html(this.template());
        return this;
    }
});


// Entrypoint
// ==========

Dashboard.init = function() {
    new Dashboard.views.Main();
};
