Dashboard = {models: {}, views: {}, collections: {}};

Dashboard.models.Account = Backbone.Model.extend({
    defaults: {
        number: null,
        name: null,
        type: null
    }
});

Dashboard.collections.Accounts = Backbone.Collection.extend({
    url: '/dashboard/accounts/',
    model: Dashboard.models.Account,
    parse: function(data) {
        return data.accounts;
    }
});

Dashboard.views.ChartOfAccounts = Backbone.View.extend({
    el: '#chart-of-accounts',
    initialize: function() {
        this.$tbody= this.$('tbody');
        this.data = new Dashboard.collections.Accounts();
        this.data.fetch({reset:true});
        this.listenTo(this.data, 'reset', this.addAll);
    },
    addOne: function (account) {
        var view = new Dashboard.views.AccountRow({model: account});
        var el = view.render().el;
        this.$tbody.append(el);
    },
    addAll: function () {
        this.$tbody.html('');
        this.data.each(this.addOne, this);
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

Dashboard.init = function() {
    new Dashboard.views.ChartOfAccounts();
};
