from __future__ import print_function, unicode_literals

from gratipay.testing import Harness, P
from gratipay.testing.email import QueuedEmailHarness


class TestIsSuspicious(Harness):
    def setUp(self):
        Harness.setUp(self)
        self.bar = self.make_participant('bar', is_admin=True)

    def toggle_is_suspicious(self):
        self.client.POST('/~foo/toggle-is-suspicious.json', auth_as='bar')

    def test_that_is_suspicious_defaults_to_None(self):
        foo = self.make_participant('foo', claimed_time='now')
        assert foo.is_suspicious is None

    def test_toggling_NULL_gives_true(self):
        self.make_participant('foo', claimed_time='now')
        self.toggle_is_suspicious()
        assert P('foo').is_suspicious is True

    def test_toggling_true_gives_false(self):
        self.make_participant('foo', is_suspicious=True, claimed_time='now')
        self.toggle_is_suspicious()
        assert P('foo').is_suspicious is False

    def test_toggling_false_gives_true(self):
        self.make_participant('foo', is_suspicious=False, claimed_time='now')
        self.toggle_is_suspicious()
        assert P('foo').is_suspicious is True

    def test_toggling_adds_event(self):
        foo = self.make_participant('foo', is_suspicious=False, claimed_time='now')
        self.toggle_is_suspicious()

        actual = self.db.one("""\
                SELECT type, payload
                  FROM events
                 WHERE CAST(payload->>'id' AS INTEGER) = %s
                   AND (payload->'values'->'is_suspicious')::text != 'null'
              ORDER BY ts DESC""",
                (foo.id,))
        assert actual == ('participant', dict(id=foo.id,
            recorder=dict(id=self.bar.id, username=self.bar.username), action='set',
            values=dict(is_suspicious=True)))

class TestIsSuspiciousEmail(QueuedEmailHarness):

    def setUp(self):
        Harness.setUp(self)
        QueuedEmailHarness.setUp(self)
        self.bar = self.make_participant('bar', is_admin=True)

    def toggle_is_suspicious(self):
        self.client.POST('/~foo/toggle-is-suspicious.json', auth_as='bar')

    def test_marking_suspicious_sends_email(self):
        self.make_participant( 'foo'
                             , claimed_time='now'
                             , email_address="foo@gratipay.com"
                             , is_suspicious=False
                              )
        self.toggle_is_suspicious()
        last_email = self.get_last_email()
        assert last_email['to'] == 'foo <foo@gratipay.com>'
        assert "We have suspended your account." in last_email['body_text']

    def test_unmarking_suspicious_sends_email(self):
        self.make_participant( 'foo'
                             , claimed_time='now'
                             , email_address="foo@gratipay.com"
                             , is_suspicious=True
                              )
        self.toggle_is_suspicious()
        last_email = self.get_last_email()
        assert last_email['to'] == 'foo <foo@gratipay.com>'
        assert "We've reactivated your account." in last_email['body_text']
