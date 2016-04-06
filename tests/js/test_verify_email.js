var assert = require('assert');
var createSession = require('./utils/session.js');

describe('verify email', function() {
    beforeEach(function(done) {
        browser
            .url('http://localhost:8537')
            .setCookie({
                name: 'session',
                value: createSession('alice')
            })
            .call(done);
    });

    afterEach(function(done) {
        browser
            .url('http://localhost:8537')
            .deleteCookie('session')
            .call(done);
    });

    it('should not throw error on clicking resend', function(done) {
        browser
            .url('http://localhost:8537/~alice/emails/verify.html?email=alice@gratipay.com&nonce=abcd')
            .getText('#content p:first-of-type', function(err, text) {
                assert.equal(text, 'The verification code for alice@gratipay.com is bad.');
            })
            .click("button.resend")
            .waitForExist('.notification.notification-success', 2000).then(function(isExisting) {
                assert(isExisting, 'Notification element not appended!');
            })
            .getText('.notification.notification-success', function(err, text) {
                var didSend = (text[1].indexOf('A verification email has been sent') > -1);
                assert(didSend, 'Expected email to be sent');
            })
            .call(done);
    });
});
