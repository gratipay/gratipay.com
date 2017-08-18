from __future__ import absolute_import, division, print_function, unicode_literals

import time

from pytest import raises

from gratipay.exceptions import NoEmailAddress, Throttled
from gratipay.testing import Harness
from gratipay.testing.email import SentEmailHarness


class TestPut(SentEmailHarness):

    def setUp(self):
        SentEmailHarness.setUp(self)
        self.alice = self.make_participant( 'alice'
                                          , claimed_time='now'
                                          , email_address='alice@example.com'
                                           )

    def test_put_puts(self):
        assert self.app.email_queue.flush() == 0
        self.app.email_queue.put(self.alice, "base")
        self.app.email_queue.put(self.alice, "base")
        self.app.email_queue.put(self.alice, "base")
        assert self.app.email_queue.flush() == 3

    def test_queueing_email_writes_timestamp(self):
        self.app.email_queue.put(self.alice, "base")

        ctime = self.db.one("SELECT EXTRACT(epoch FROM ctime) FROM email_messages")
        assert abs(ctime - time.time()) < 300

    def test_only_user_initiated_messages_count_towards_throttling(self):
        self.app.email_queue.put(self.alice, "base")
        self.app.email_queue.put(self.alice, "base", _user_initiated=False)
        self.app.email_queue.put(self.alice, "base")
        self.app.email_queue.put(self.alice, "base", _user_initiated=False)
        self.app.email_queue.put(self.alice, "base")
        self.app.email_queue.put(self.alice, "base", _user_initiated=False)
        raises(Throttled, self.app.email_queue.put, self.alice, "branch")

    def test_flushing_queue_resets_throttling(self):
        self.app.email_queue.put(self.alice, "base")
        self.app.email_queue.put(self.alice, "base")
        self.app.email_queue.put(self.alice, "base")
        assert self.app.email_queue.flush() == 3
        self.app.email_queue.put(self.alice, "base")


class TestFlush(SentEmailHarness):

    def put_message(self, email_address='larry@example.com'):
        larry = self.make_participant('larry', email_address=email_address)
        self.app.email_queue.put(larry, "base")

    def test_can_flush_an_email_from_the_queue(self):
        self.put_message()

        assert self.db.one("SELECT * FROM email_messages").spt_name == "base"
        self.app.email_queue.flush()
        assert self.count_email_messages() == 1
        last_email = self.get_last_email()
        assert last_email['to'] == 'larry <larry@example.com>'
        expected = "Something not right?"
        assert expected in last_email['body_text']
        assert self.db.one("SELECT * FROM email_messages").result == ''

    def test_flushing_an_email_without_address_logs_a_failure(self):
        self.put_message(email_address=None)
        raises(NoEmailAddress, self.app.email_queue.flush)
        assert self.count_email_messages() == 0
        assert self.db.one("SELECT * FROM email_messages").result == "NoEmailAddress()"

    def test_flush_does_not_resend_dead_letters(self):
        self.put_message()
        self.db.run("UPDATE email_messages SET result='foo error'")
        self.app.email_queue.flush()
        assert self.count_email_messages() == 0

    def test_failed_flushes_are_marked_as_dead_letters(self):
        # patch mailer
        class SomeProblem(Exception): pass
        def failer(*a, **kw): raise SomeProblem()
        self.app.email_queue._mailer.send_email = failer

        # queue a message
        self.put_message()
        assert self.db.one("SELECT result FROM email_messages") is None

        # now try to send it
        raises(SomeProblem, self.app.email_queue.flush)
        assert self.count_email_messages() == 0  # nothing sent
        assert self.db.one("SELECT result FROM email_messages") == 'SomeProblem()'

class TestLogMetrics(Harness):

    def setUp(self):
        Harness.setUp(self)
        self._log_every = self.app.email_queue.log_every
        self.app.email_queue.log_every = 1

    def tearDown(self):
        self.app.email_queue.log_every = self._log_every
        Harness.tearDown(self)

    def test_log_metrics(self):
        alice = self.make_participant( 'alice'
                                     , claimed_time='now'
                                     , email_address='alice@example.com'
                                      )

        self.app.email_queue.put(alice, "base")
        self.app.email_queue.put(alice, "base")
        self.app.email_queue.put(alice, "base")

        self.db.run("UPDATE email_messages SET result='foo error' "
                    "WHERE id IN (SELECT id FROM email_messages LIMIT 1)")

        captured = {}
        def p(message): captured['message'] = message
        self.app.email_queue.log_metrics(_print=p)
        assert captured['message'] == \
                  'count#email_queue_sent=0 count#email_queue_failed=1 count#email_queue_pending=2'
