# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import re
from gratipay.testing import BrowserHarness, QueuedEmailHarness


class Row(object):
    """Represent one row in the listing on the emails page.
    """

    def __init__(self, harness, element):
        self.harness = harness
        self.element = element

    def buttons(self):
        """Return a list of the text of all buttons in the row.
        """
        return [b.text for b in self.harness.css('button', self.element)]

    def click(self, text):
        """Given the text of a button in the row, click the button.
        """
        [b for b in self.harness.css('button', self.element) if b.text == text][0].click()

    def add(self, email_address, expecting_reload=True):
        """Given an email address, add it via the UI. Only works for add rows!
        """
        self.click('Add an email address')
        self.harness.css('input', self.element).fill(email_address)
        if expecting_reload:
            with self.harness.page_reload_afterwards():
                self.click('Send verification')
        else:
            self.click('Send verification')

    def remove(self):
        with self.harness.page_reload_afterwards():
            self.click('Remove')


class Page(object):
    """Represent the emails page.
    """

    def __init__(self, harness):
        self.harness = harness

    @property
    def rows(self):
        return [Row(self.harness, element) for element in self.harness.css('.emails.listing tr')]

    @property
    def names(self):
        out = [x.text for x in self.harness.css('.emails.listing tr.existing .listing-name')]
        add_row = self.harness.css('.emails.listing tr.add')
        if add_row:
            out.append('<add form>')
        return out

    def add_and_verify(self, email_address):
        self.add(email_address)
        assert self.harness.pop_email_message()['subject'] == 'New activity on your account'
        self.harness.visit(self.harness.get_verification_link())


class Tests(BrowserHarness, QueuedEmailHarness):

    def get_verification_link(self):
        """Return the verification link sent via email.
        """
        verification_email = self.pop_email_message()
        verification_link = re.match( r'.*?(http.*?$).*'
                                    , verification_email['body_text']
                                    , re.DOTALL | re.MULTILINE
                                     ).groups()[0]
        return verification_link

    def test(self):
        self.alice = self.make_participant('alice', claimed_time='now')
        self.sign_in('alice')
        self.visit('/~alice/emails/')
        page = Page(self)  # state manager

        # Starts clean.
        assert len(page.rows) == 1
        row = page.rows[0]
        assert row.buttons() == ['Add an email address', '', '']

        # Can toggle add form on and off and on again.
        row.click('Add an email address')
        assert row.buttons() == ['', 'Send verification', 'Cancel']
        row.click('Cancel')
        assert row.buttons() == ['Add an email address', '', '']

        # Can submit add form.
        row.add('alice@example.com')
        assert len(page.rows) == 1  # no add form when verification pending
        row = page.rows[0]
        assert row.buttons() == ['Resend', 'Remove']

        # Can resend verification.
        self.pop_email_message()  # oops! lost the verification message
        row.click('Resend')
        assert self.wait_for_success() == 'Check your inbox for a verification link.'

        # Can verify.
        self.visit(self.get_verification_link())
        assert self.css('#content h1').text == 'Success!'

        # Now listed as primary -- nothing to be done with primary.
        self.visit('/~alice/emails/')
        assert len(page.rows) == 2
        row = page.rows[0]
        assert row.buttons() == []
        assert row.element.text.endswith('Your primary email address')

        # ... but the add form is back. Can we re-add the same?
        row = page.rows[1]
        row.add('alice@example.com', expecting_reload=False)
        assert self.wait_for_error() == 'You have already added and verified that address.'  # No!
        row.click('Cancel')

        # Let's add another!
        row.add('alice@example.net')
        assert self.pop_email_message()['subject'] == 'New activity on your account'
        self.visit(self.get_verification_link())
        with self.page_reload_afterwards():
            self.css('#content a').click()  # back over to /emails/

        # Now we should have a primary and a linked address, and an add row.
        assert page.names == ['alice@example.com', 'alice@example.net', '<add form>']
        assert page.rows[2].buttons() == ['Add an email address', '', '']

        # We can promote the secondary account to primary.
        with self.page_reload_afterwards():
            page.rows[1].click('Set as primary')

        # ... and now the order is reversed.
        assert page.names == ['alice@example.net', 'alice@example.com', '<add form>']

        # We can remove the (new) secondary account.
        page.rows[1].remove()
        assert page.names == ['alice@example.net', '<add form>']

        # Add another again.
        page.rows[1].add('alice@example.org')
        assert self.pop_email_message()['subject'] == 'New activity on your account'
        verification_link = self.get_verification_link()

        # No add form while pending
        assert page.names == ['alice@example.net', 'alice@example.org']

        # But we can remove a pending verification.
        page.rows[1].remove()
        assert page.names == ['alice@example.net', '<add form>']

        # The link no longer works, of course.
        self.visit(verification_link)
        assert self.css('#content h1').text == 'Bad Info'
