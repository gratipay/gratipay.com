var assert = require('assert');

describe('homepage', function() {
    it('should render copy correctly', function(done) {
        browser
            .url('http://localhost:8537')
            .getText('#header .sign-in', function(err, text) {
                assert.equal(text, 'Sign in');
            })
            .call(done);
    });
});
