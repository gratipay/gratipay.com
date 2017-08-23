# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import re
from gratipay.testing import BrowserHarness, QueuedEmailHarness


class Tests(BrowserHarness, QueuedEmailHarness):


    def test(self):
        self.alice = self.make_participant('alice', claimed_time='now')
        self.sign_in('alice')
        self.visit('/~alice/emails/')

        # Helpers

        buttons = lambda: [b.text for b in self.css('button', row)]
        click = lambda text: [b for b in self.css('button', row) if b.text == text][0].click()

        def add(email_address):
            click('Add an email address')
            self.css('input', row).fill(email_address)
            click('Send verification')

        def get_verification_link():
            verification_email = self.pop_email_message()
            verification_link = re.match( r'.*?(http.*?$).*'
                                        , verification_email['body_text']
                                        , re.DOTALL | re.MULTILINE
                                         ).groups()[0]
            return verification_link


        # Starts clean.
        rows = self.css('#content tr')
        assert len(rows) == 1
        row = rows[0]
        assert buttons() == ['Add an email address', '', '']

        # Can toggle add form on and off and on again.
        click('Add an email address')
        assert buttons() == ['', 'Send verification', 'Cancel']
        click('Cancel')
        assert buttons() == ['Add an email address', '', '']

        # Can submit add form.
        add('alice@example.com')
        row = self.wait_for('tr.existing')
        assert buttons() == ['Resend verification']
        self.pop_email_message()  # throw away verification message

        # Can resend verification.
        click('Resend verification')
        assert self.wait_for_success() == 'Check your inbox for a verification link.'

        # Can verify.
        self.visit(get_verification_link())
        assert self.css('#content h1').text == 'Success!'

        # Now listed as primary -- nothing to be done with primary.
        self.visit('/~alice/emails/')
        rows = self.css('.emails.listing tr')
        assert len(rows) == 2
        row = rows[0]
        assert buttons() == []
        assert row.text.endswith('Your primary email address')

        # ... but the add form is back. Can we re-add the same?
        row = rows[1]
        add('alice@example.com')
        assert self.wait_for_error() == 'You have already added and verified that address.'  # No!
        click('Cancel')

        # Let's add another!
        add('alice@example.net')
        self.wait_for('.emails.listing tr')
        assert self.pop_email_message()['subject'] == 'New activity on your account'
        self.visit(get_verification_link())

        # Now we should have a primary and a linked address, and an add row.
        self.css('#content a').click()
        rows = self.wait_for('.emails.listing tr')
        assert len(rows) == 3
        email_addresses = [x.text for x in self.css('.existing .listing-name')]
        assert email_addresses == ['alice@example.com', 'alice@example.net']
        row = rows[2]
        assert buttons() == ['Add an email address', '', '']

        # We can promote the secondary account to primary.
        row = rows[1]
        click('Set as primary')
        rows = self.wait_for('.emails.listing tr')
        assert len(rows) == 3

        # ... and now the order is reversed.
        email_addresses = [x.text for x in self.css('.existing .listing-name')]
        assert email_addresses == ['alice@example.net', 'alice@example.com']

        # We can remove the (new) secondary account.
        row = rows[1]
        click('Remove')
        self.wait_to_disappear('tr[data-email="alice@example.com"]')
        assert len(self.css('.emails.listing tr')) == 2
