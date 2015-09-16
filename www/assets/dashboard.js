Dashboard = {};

Dashboard.accounts = Backbone.View.extend({
    el: '.foo',
    initialize: function() {
        this.$table = this.$('table');
        this.data = new Dashboard.accounts.Accounts();
        this.data.fetch({reset:true});
        this.listenTo(this.data, 'reset', this.addAll);
    },
    addOne: function (account) {
        var view = new Dashboard.accounts.Row({model: account});
        var el = view.render().el;
        this.$table.append(el);
    },
    addAll: function () {
        this.$table.html('');
        this.data.each(this.addOne, this);
    }
});

Dashboard.accounts.Row = Backbone.View.extend({
    template: _.template('<tr><td><%= number %></td><td><%= name %></td><td><%= kind %></td></tr>'),
    render: function() {
        console.log(this);
        this.$el.html(this.template(this.model.toJSON()));
        return this;
    }
});

Dashboard.accounts.Account = Backbone.Model.extend({
    defaults: {
        number: null,
        name: null,
        kind: null
    }
});

Dashboard.accounts.Accounts = Backbone.Collection.extend({
    url: '/dashboard/accounts/',
    model: Dashboard.accounts.Account,
    parse: function(data) {
        return data.accounts;
    }
});

Dashboard.init = function() {
    new Dashboard.accounts();
};
