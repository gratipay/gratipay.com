from __future__ import absolute_import, division, print_function, unicode_literals

import json
import Queue
import sys
import threading
import time
import urllib

import mock
from pytest import raises

from gratipay.exceptions import CannotRemovePrimaryEmail, EmailTaken, EmailNotVerified
from gratipay.exceptions import TooManyEmailAddresses, Throttled, EmailAlreadyVerified
from gratipay.exceptions import EmailNotOnFile, ProblemChangingEmail
from gratipay.testing import P, Harness
from gratipay.testing.email import QueuedEmailHarness, SentEmailHarness
from gratipay.models.package import NPM, Package
from gratipay.models.participant import email as _email
from gratipay.utils import encode_for_querystring
from gratipay.cli import queue_branch_email as _queue_branch_email


class Alice(QueuedEmailHarness):

    def setUp(self):
        QueuedEmailHarness.setUp(self)
        self.alice = self.make_participant('alice', claimed_time='now')

    def add(self, participant, address, _flush=False):
        participant.start_email_verification(address)
        nonce = participant.get_email(address).nonce
        result = participant.finish_email_verification(address, nonce)
        assert result == (_email.VERIFICATION_SUCCEEDED, [], None)
        if _flush:
            self.app.email_queue.flush()


class TestEndpoints(Alice):

    def hit_email_spt(self, action, address, user='alice', package_ids=[], should_fail=False):
        f = self.client.PxST if should_fail else self.client.POST

        # Aspen's test client should really support URL-encoding POST data for
        # us, but it doesn't (it only supports multipart, which I think maybe
        # doesn't work because of other Aspen bugs around multiple package_id
        # values in the same POST body in that case?), so let's do that
        # ourselves.

        data = [ ('action', action)
               , ('address', address)
                ] + [('package_id', str(p)) for p in package_ids]
        body = urllib.urlencode(data)

        response = f( '/~alice/emails/modify.json'
                    , body=body
                    , content_type=b'application/x-www-form-urlencoded'
                    , auth_as=user
                    , HTTP_ACCEPT_LANGUAGE=b'en'
                     )
        if issubclass(response.__class__, (Throttled, ProblemChangingEmail)):
            response.render_body({'_': lambda a: a})
        return response

    def hit_verify_spt(self, email, nonce, username='alice', should_fail=False):
        # Email address is encoded in url.
        url = '/~%s/emails/verify.html?email2=%s&nonce=%s'
        url %= (username, encode_for_querystring(email), nonce)
        f = self.client.GxT if should_fail else self.client.GET
        return f(url, auth_as=username)

    def verify_and_change_email(self, old_email, new_email, username='alice', _flush=True):
        self.hit_email_spt('add-email', old_email)
        nonce = P(username).get_email(old_email).nonce
        self.hit_verify_spt(old_email, nonce)
        self.hit_email_spt('add-email', new_email)
        if _flush:
            self.app.email_queue.flush()

    def test_participant_can_start_email_verification(self):
        response = self.hit_email_spt('add-email', 'alice@gratipay.com')
        assert json.loads(response.body) == 'Check your inbox for a verification link.'

    def test_starting_email_verification_triggers_verification_email(self):
        self.hit_email_spt('add-email', 'alice@gratipay.com')
        assert self.count_email_messages() == 1
        last_email = self.get_last_email()
        assert last_email['to'] == 'alice <alice@gratipay.com>'
        expected = "We've received a request to connect alice@gratipay.com to the alice account"
        assert expected in last_email['body_text']

    def test_email_address_is_encoded_in_sent_verification_link(self):
        address = 'alice@gratipay.com'
        encoded = encode_for_querystring(address)
        self.hit_email_spt('add-email', address)
        last_email = self.get_last_email()
        assert "~alice/emails/verify.html?email2="+encoded in last_email['body_text']

    def test_verification_email_doesnt_contain_unsubscribe(self):
        self.hit_email_spt('add-email', 'alice@gratipay.com')
        last_email = self.get_last_email()
        assert "To stop receiving" not in last_email['body_text']

    def test_verifying_second_email_sends_verification_notice(self):
        self.verify_and_change_email('alice1@example.com', 'alice2@example.com', _flush=False)
        assert self.count_email_messages() == 3
        last_email = self.get_last_email()
        self.app.email_queue.flush()
        assert last_email['to'] == 'alice <alice1@example.com>'
        expected = "We are connecting alice2@example.com to the alice account on Gratipay"
        assert expected in last_email['body_text']

    def test_post_anon_returns_401(self):
        response = self.hit_email_spt('add-email', 'anon@example.com', user=None, should_fail=True)
        assert response.code == 401

    def test_post_with_no_at_symbol_is_400(self):
        response = self.hit_email_spt('add-email', 'gratipay.com', should_fail=True)
        assert response.code == 400

    def test_post_with_no_period_symbol_is_400(self):
        response = self.hit_email_spt('add-email', 'test@gratipay', should_fail=True)
        assert response.code == 400

    def test_post_with_long_address_is_okay(self):
        response = self.hit_email_spt('add-email', ('a'*242) + '@example.com')
        assert response.code == 200

    def test_post_with_looooong_address_is_400(self):
        response = self.hit_email_spt('add-email', ('a'*243) + '@example.com', should_fail=True)
        assert response.code == 400

    def test_post_too_quickly_is_400(self):
        self.hit_email_spt('add-email', 'alice@example.com')
        self.hit_email_spt('add-email', 'alice+a@example.com')
        self.hit_email_spt('add-email', 'alice+b@example.com')
        response = self.hit_email_spt('add-email', 'alice+c@example.com', should_fail=True)
        assert response.code == 400
        assert 'too quickly' in response.body

    def test_verify_email_without_adding_email(self):
        response = self.hit_verify_spt('', 'sample-nonce')
        assert 'Bad Info' in response.body

    def test_verify_email_wrong_nonce(self):
        self.hit_email_spt('add-email', 'alice@example.com')
        nonce = 'fake-nonce'
        result = self.alice.finish_email_verification('alice@gratipay.com', nonce)
        assert result == (_email.VERIFICATION_FAILED, None, None)
        self.hit_verify_spt('alice@example.com', nonce)
        expected = None
        actual = P('alice').email_address
        assert expected == actual

    def test_verify_email_a_second_time_returns_redundant(self):
        address = 'alice@example.com'
        self.hit_email_spt('add-email', address)
        nonce = self.alice.get_email(address).nonce
        self.alice.finish_email_verification(address, nonce)
        result = self.alice.finish_email_verification(address, nonce)
        assert result == (_email.VERIFICATION_REDUNDANT, None, None)

    def test_verify_email_expired_nonce_fails(self):
        address = 'alice@example.com'
        self.hit_email_spt('add-email', address)
        self.db.run("""
            UPDATE emails
               SET verification_start = (now() - INTERVAL '25 hours')
             WHERE participant_id = %s;
        """, (self.alice.id,))
        nonce = self.alice.get_email(address).nonce
        result = self.alice.finish_email_verification(address, nonce)
        assert result == (_email.VERIFICATION_FAILED, None, None)
        actual = P('alice').email_address
        assert actual == None

    def test_finish_email_verification(self):
        self.hit_email_spt('add-email', 'alice@example.com')
        nonce = self.alice.get_email('alice@example.com').nonce
        assert self.hit_verify_spt('alice@example.com', nonce).code == 200
        assert P('alice').email_address == 'alice@example.com'

    def test_empty_email_fails(self):
        for empty in ('', '    '):
            result = self.alice.finish_email_verification(empty, 'foobar')
            assert result == (_email.VERIFICATION_FAILED, None, None)

    def test_empty_nonce_fails(self):
        for empty in ('', '    '):
            result = self.alice.finish_email_verification('foobar', empty)
            assert result == (_email.VERIFICATION_FAILED, None, None)

    def test_email_verification_is_backwards_compatible(self):
        """Test email verification still works with unencoded email in verification link.
        """
        self.hit_email_spt('add-email', 'alice@example.com')
        nonce = self.alice.get_email('alice@example.com').nonce
        url = '/~alice/emails/verify.html?email=alice@example.com&nonce='+nonce
        self.client.GET(url, auth_as='alice')
        expected = 'alice@example.com'
        actual = P('alice').email_address
        assert expected == actual

    def test_verified_email_is_not_changed_after_update(self):
        self.verify_and_change_email('alice@example.com', 'alice@example.net')
        expected = 'alice@example.com'
        actual = P('alice').email_address
        assert expected == actual

    def test_get_emails(self):
        self.verify_and_change_email('alice@example.com', 'alice@example.net')
        emails = self.alice.get_emails()
        assert len(emails) == 2

    def test_verify_email_after_update(self):
        self.verify_and_change_email('alice@example.com', 'alice@example.net')
        nonce = self.alice.get_email('alice@example.net').nonce
        self.hit_verify_spt('alice@example.net', nonce)
        expected = 'alice@example.com'
        actual = P('alice').email_address
        assert expected == actual

    def test_nonce_is_not_reused_when_resending_email(self):
        self.hit_email_spt('add-email', 'alice@example.com')
        nonce1 = self.alice.get_email('alice@example.com').nonce
        self.hit_email_spt('resend', 'alice@example.com')
        nonce2 = self.alice.get_email('alice@example.com').nonce
        assert nonce1 != nonce2

    def test_emails_page_shows_emails(self):
        self.verify_and_change_email('alice@example.com', 'alice@example.net')
        body = self.client.GET("/~alice/emails/", auth_as="alice").body
        assert 'alice@example.com' in body
        assert 'alice@example.net' in body

    def test_set_primary(self):
        self.verify_and_change_email('alice@example.com', 'alice@example.net')
        self.verify_and_change_email('alice@example.net', 'alice@example.org')
        self.hit_email_spt('set-primary', 'alice@example.com')

    def test_cannot_set_primary_to_unverified(self):
        with self.assertRaises(EmailNotVerified):
            self.hit_email_spt('set-primary', 'alice@example.com')

    def test_remove_email(self):
        # Can remove unverified
        self.hit_email_spt('add-email', 'alice@example.com')
        self.hit_email_spt('remove', 'alice@example.com')

        # Can remove verified
        self.verify_and_change_email('alice@example.com', 'alice@example.net')
        self.verify_and_change_email('alice@example.net', 'alice@example.org')
        self.hit_email_spt('remove', 'alice@example.net')

        # Cannot remove primary
        with self.assertRaises(CannotRemovePrimaryEmail):
            self.hit_email_spt('remove', 'alice@example.com')


    def test_participant_can_verify_a_package_along_with_email(self):
        foo = self.make_package(name='foo', emails=['alice@gratipay.com'])
        response = self.hit_email_spt( 'start-verification'
                                     , 'alice@gratipay.com'
                                     , package_ids=[foo.id]
                                      )
        assert json.loads(response.body) == 'Check your inbox for a verification link.'
        assert self.db.all('select package_id from claims order by package_id') == [foo.id]

    def test_participant_cant_verify_packages_with_add_email_or_resend(self):
        foo = self.make_package(name='foo', emails=['alice@gratipay.com'])
        for action in ('add-email', 'resend'):
            assert self.hit_email_spt( action
                                     , 'alice@gratipay.com'
                                     , package_ids=[foo.id]
                                     , should_fail=True
                                      ).code == 400

    def test_participant_can_verify_multiple_packages_along_with_email(self):
        package_ids = [self.make_package(name=name, emails=['alice@gratipay.com']).id
                       for name in ('foo', 'bar', 'baz', 'buz')]
        response = self.hit_email_spt( 'start-verification'
                                     , 'alice@gratipay.com'
                                     , package_ids=package_ids
                                      )
        assert json.loads(response.body) == 'Check your inbox for a verification link.'
        assert self.db.all('select package_id from claims order by package_id') == package_ids

    def test_package_verification_fails_if_email_not_listed(self):
        foo = self.make_package()
        response = self.hit_email_spt( 'start-verification'
                                     , 'bob@gratipay.com'
                                     , package_ids=[foo.id]
                                     , should_fail=True
                                      )
        assert response.code == 400
        assert self.db.all('select package_id from claims order by package_id') == []

    def test_package_verification_fails_if_package_id_is_garbage(self):
        response = self.hit_email_spt( 'start-verification'
                                     , 'bob@gratipay.com'
                                     , package_ids=['cheese monkey']
                                     , should_fail=True
                                      )
        assert response.code == 400
        assert self.db.all('select package_id from claims order by package_id') == []

    def test_package_reverification_succeeds_if_package_is_already_claimed_by_self(self):
        foo = self.make_package()
        self.claim_package('alice', foo)
        response = self.hit_email_spt( 'start-verification'
                                     , 'alice@example.com'
                                     , package_ids=[foo.id]
                                      )
        assert response.code == 200

    def test_package_verification_fails_if_package_is_already_claimed_by_other(self):
        self.make_participant('bob', claimed_time='now', email_address='bob@example.com')
        foo = self.make_package(emails=['alice@example.com', 'bob@example.com'])
        self.claim_package('bob', foo)
        response = self.hit_email_spt( 'start-verification'
                                     , 'alice@example.com'
                                     , package_ids=[foo.id]
                                     , should_fail=True
                                      )
        assert response.code == 400


class TestFunctions(Alice):

    def test_cannot_update_email_to_already_verified(self):
        bob = self.make_participant('bob', claimed_time='now')
        self.add(self.alice, 'alice@gratipay.com')

        with self.assertRaises(EmailTaken):
            bob.start_email_verification('alice@gratipay.com')
            nonce = bob.get_email('alice@gratipay.com').nonce
            bob.finish_email_verification('alice@gratipay.com', nonce)

        email_alice = P('alice').email_address
        assert email_alice == 'alice@gratipay.com'

    def test_html_escaping(self):
        self.alice.start_email_verification("foo'bar@example.com")
        last_email = self.get_last_email()
        assert 'foo&#39;bar' in last_email['body_html']
        assert '&#39;' not in last_email['body_text']

    def test_npm_package_name_is_handled_safely(self):
        foo = self.make_package(name='<script>')
        self.alice.start_email_verification("alice@example.com", foo)
        last_email = self.get_last_email()
        assert '<b>&lt;script&gt;</b>' in last_email['body_html']
        assert '<script>' in last_email['body_text']

    def test_queueing_email_is_throttled(self):
        self.app.email_queue.put(self.alice, "base")
        self.app.email_queue.put(self.alice, "base")
        self.app.email_queue.put(self.alice, "base")
        raises(Throttled, self.app.email_queue.put, self.alice, "base")

    def test_queueing_email_writes_timestamp(self):
        self.app.email_queue.put(self.alice, "base")

        ctime = self.db.one("SELECT EXTRACT(epoch FROM ctime) FROM email_queue")
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
        self.add(self.alice, 'alice@example.com')
        assert self.app.email_queue.flush() == 1
        self.app.email_queue.put(self.alice, "base")
        self.app.email_queue.put(self.alice, "base")
        self.app.email_queue.put(self.alice, "base")
        assert self.app.email_queue.flush() == 3
        self.app.email_queue.put(self.alice, "base")

    def test_log_metrics(self):
        self.app.email_queue.put(self.alice, "base")
        self.app.email_queue.put(self.alice, "base")
        self.app.email_queue.put(self.alice, "base")

        self.db.run("UPDATE email_queue SET dead = 'true' WHERE id IN (SELECT id FROM email_queue LIMIT 1)")

        mock_print = mock.Mock()

        self.app.email_queue.log_metrics(_print=mock_print)
        mock_print.assert_called_once_with('count#email_queue_dead=1 count#email_queue_total=3')


class FlushEmailQueue(SentEmailHarness):

    def put_message(self, email_address='larry@example.com'):
        larry = self.make_participant('larry', email_address=email_address)
        self.app.email_queue.put(larry, "base")

    def test_can_flush_an_email_from_the_queue(self):
        self.put_message()

        assert self.db.one("SELECT spt_name FROM email_queue") == "base"
        self.app.email_queue.flush()
        assert self.count_email_messages() == 1
        last_email = self.get_last_email()
        assert last_email['to'] == 'larry <larry@example.com>'
        expected = "Something not right?"
        assert expected in last_email['body_text']
        assert self.db.one("SELECT spt_name FROM email_queue") is None

    def test_flushing_an_email_without_address_just_skips_it(self):
        self.put_message(email_address=None)

        assert self.db.one("SELECT spt_name FROM email_queue") == "base"
        self.app.email_queue.flush()
        assert self.count_email_messages() == 0
        assert self.db.one("SELECT spt_name FROM email_queue") is None

    def test_we_dont_resend_dead_letters(self):
        self.put_message()
        self.db.run("UPDATE email_queue SET dead=true")
        self.app.email_queue.flush()
        assert self.count_email_messages() == 0

    def test_failed_flushes_are_marked_as_dead_letters(self):

        # patch mailer
        class SomeProblem(Exception): pass
        def failer(*a, **kw): raise SomeProblem()
        self.app.email_queue._mailer.send_email = failer

        # queue a message
        self.put_message()
        assert not self.db.one("SELECT dead FROM email_queue")

        # now try to send it
        raises(SomeProblem, self.app.email_queue.flush)
        assert self.count_email_messages() == 0  # nothing sent
        assert self.db.one("SELECT dead FROM email_queue")


class TestGetRecentlyActiveParticipants(QueuedEmailHarness):

    def check(self):
        return _queue_branch_email.get_recently_active_participants(self.db)

    def test_gets_recently_active_participants(self):
        alice = self.make_participant_with_exchange('alice')
        assert self.check() == [alice]

    def test_ignores_participants_with_no_exchanges(self):
        self.make_participant('alice', claimed_time='now', email_address='a@example.com')
        assert self.check() == []

    def test_ignores_participants_with_no_recent_exchanges(self):
        self.make_participant_with_exchange('alice')
        self.db.run("UPDATE exchanges SET timestamp = timestamp - '181 days'::interval")
        assert self.check() == []

    def test_keeps_participants_straight(self):
        alice = self.make_participant_with_exchange('alice')
        bob = self.make_participant_with_exchange('bob')
        self.make_participant_with_exchange('carl')
        self.db.run("UPDATE exchanges SET timestamp = timestamp - '181 days'::interval "
                    "WHERE participant='carl'")
        self.make_participant('dana', claimed_time='now', email_address='d@example.com')
        assert self.check() == [alice, bob]


class TestQueueBranchEmail(QueuedEmailHarness):

    def queue_branch_email(self, username, _argv=None, _input=None, _print=None):
        _argv = ['', username] if _argv is None else _argv
        _input = _input or (lambda prompt: 'y')
        stdout, stderr = [], []
        def _print(string, file=None):
            buf = stderr if file is sys.stderr else stdout
            buf.append(str(string))
        _print = _print or (lambda *a, **kw: None)
        try:
            _queue_branch_email.main(_argv, _input, _print, self.app)
        except SystemExit as exc:
            retcode = exc.args[0]
        else:
            retcode = 0
        return retcode, stdout, stderr


    def test_is_fine_with_no_participants(self):
        retcode, output, errors = self.queue_branch_email('all')
        assert retcode == 0
        assert output == ['Okay, you asked for it!', '0']
        assert errors == []
        assert self.count_email_messages() == 0

    def test_queues_for_one_participant(self):
        alice = self.make_participant_with_exchange('alice')
        retcode, output, errors = self.queue_branch_email('all')
        assert retcode == 0
        assert output == [ 'Okay, you asked for it!'
                         , '1'
                         , 'spotcheck: alice@example.com (alice={})'.format(alice.id)
                          ]
        assert errors == ['   1 queuing for alice@example.com (alice={})'.format(alice.id)]
        assert self.count_email_messages() == 1

    def test_queues_for_two_participants(self):
        alice = self.make_participant_with_exchange('alice')
        bob = self.make_participant_with_exchange('bob')
        retcode, output, errors = self.queue_branch_email('all')
        assert retcode == 0
        assert output[:2] == ['Okay, you asked for it!', '2']
        assert errors == [ '   1 queuing for alice@example.com (alice={})'.format(alice.id)
                         , '   2 queuing for bob@example.com (bob={})'.format(bob.id)
                          ]
        assert self.count_email_messages() == 2

    def test_constrains_to_one_participant(self):
        self.make_participant_with_exchange('alice')
        bob = self.make_participant_with_exchange('bob')
        retcode, output, errors = self.queue_branch_email('bob')
        assert retcode == 0
        assert output == [ 'Okay, just bob.'
                         , '1'
                         , 'spotcheck: bob@example.com (bob={})'.format(bob.id)
                          ]
        assert errors == ['   1 queuing for bob@example.com (bob={})'.format(bob.id)]
        assert self.count_email_messages() == 1

    def test_bails_if_told_to(self):
        retcode, output, errors = self.queue_branch_email('all', _input=lambda prompt: 'n')
        assert retcode == 1
        assert output == []
        assert errors == []
        assert self.count_email_messages() == 0


class StartEmailVerification(Alice):

    def test_starts_email_verification(self):
        self.alice.start_email_verification('alice@example.com')
        assert self.get_last_email()['subject'] == 'Connect to alice on Gratipay?'

    def test_raises_if_already_verified(self):
        self.add(self.alice, 'alice@example.com')
        raises(EmailAlreadyVerified, self.alice.start_email_verification, 'alice@example.com')

    def test_raises_if_already_taken(self):
        self.add(self.alice, 'alice@example.com')
        bob = self.make_participant('bob', claimed_time='now')
        raises(EmailTaken, bob.start_email_verification, 'alice@example.com')

    def test_maxes_out_at_10(self):
        for i in range(10):
            self.add(self.alice, 'alice-{}@example.com'.format(i), _flush=True)
        raises(TooManyEmailAddresses, self.alice.start_email_verification, 'alice@example.com')

    def test_can_include_packages_in_verification(self):
        foo = self.make_package()
        self.alice.start_email_verification('alice@example.com', foo)
        assert self.get_last_email()['subject'] == 'Connect to alice on Gratipay?'
        assert self.db.one('select package_id from claims') == foo.id

    def test_can_claim_package_even_when_address_already_verified(self):
        self.add(self.alice, 'alice@example.com')
        foo = self.make_package()
        self.alice.start_email_verification('alice@example.com', foo)
        assert self.get_last_email()['subject'] == 'Connect to alice on Gratipay?'
        assert self.db.one('select package_id from claims') == foo.id

    def test_claiming_package_with_verified_address_doesnt_count_against_max(self):
        for i in range(10):
            self.add(self.alice, 'alice-{}@example.com'.format(i), _flush=True)
        foo = self.make_package(emails=['alice-4@example.com'])
        self.alice.start_email_verification('alice-4@example.com', foo)
        assert self.db.one('select package_id from claims') == foo.id

    def test_claiming_package_with_someone_elses_verified_address_is_a_no_go(self):
        self.add(self.alice, 'alice@example.com')
        bob = self.make_participant('bob', claimed_time='now')
        foo = self.make_package()
        raises(EmailTaken, bob.start_email_verification, 'alice@example.com', foo)

    def test_claiming_package_with_an_address_not_on_file_is_a_no_go(self):
        foo = self.make_package(emails=['bob@example.com'])
        raises(EmailNotOnFile, self.alice.start_email_verification, 'alice@example.com', foo)

    def test_restarting_verification_clears_old_claims(self):
        foo = self.make_package()
        _start = lambda: self.alice.start_email_verification('alice@example.com', foo)
        _nonce = lambda: self.db.one('select nonce from claims')
        _start()
        nonce = _nonce()
        _start()
        result = self.alice.finish_email_verification('alice@example.com', nonce)
        assert result == (_email.VERIFICATION_FAILED, None, None)
        assert nonce != _nonce()

    def test_restarting_verification_also_clears_old_claims_when_address_preverified(self):
        foo = self.make_package()
        self.add_and_verify_email(self.alice, 'alice@example.com')
        _start = lambda: self.alice.start_email_verification('alice@example.com', foo)
        _nonce = lambda: self.db.one('select nonce from claims')
        _start()
        nonce = _nonce()
        _start()
        result = self.alice.finish_email_verification('alice@example.com', nonce)
        assert result == (_email.VERIFICATION_FAILED, None, None)
        assert nonce != _nonce()

    def test_finishing_verification_clears_competing_claims_and_emails(self):
        bob = self.make_participant('bob', claimed_time='now')
        foo = self.make_package()

        self.alice.start_email_verification('alice@example.com', foo)
        anonce = self.alice.get_emails()[0].nonce

        bob.start_email_verification('alice@example.com', foo)
        bnonce = bob.get_emails()[0].nonce

        _emails = lambda: self.db.all('select participant_id as i from emails order by i')
        _claims = lambda: dict(self.db.all('select nonce, package_id from claims'))

        assert _claims() == {anonce: foo.id, bnonce: foo.id}
        assert _emails() == [self.alice.id, bob.id]

        result = self.alice.finish_email_verification('alice@example.com', anonce)
        assert result == (_email.VERIFICATION_SUCCEEDED, [foo], True)

        assert _claims() == {}
        assert _emails() == [self.alice.id]

        result = bob.finish_email_verification('alice@example.com', bnonce)
        assert result == (_email.VERIFICATION_FAILED, None, None)


class RemoveEmail(Alice):

    def test_removing_email_clears_claims(self):
        foo = self.make_package()
        self.alice.start_email_verification('alice@example.com', foo)
        _claims = lambda: self.db.all('select package_id from claims')
        assert _claims() == [foo.id]
        self.alice.remove_email('alice@example.com')
        assert _claims() == []


class GetEmailVerificationLink(Harness):

    def get_claims(self):
        return self.db.all('''
            SELECT name
              FROM claims c
              JOIN packages p
                ON c.package_id = p.id
          ORDER BY name
        ''')

    def test_returns_a_link(self):
        with self.db.get_cursor() as c:
            alice = self.make_participant('alice')
            link = alice.get_email_verification_link(c, 'alice@example.com')
        assert link.startswith('/~alice/emails/verify.html?email2=YWxpY2VAZXhhbXBsZS5jb20~&nonce=')

    def test_makes_no_claims_by_default(self):
        with self.db.get_cursor() as c:
            self.make_participant('alice').get_email_verification_link(c, 'alice@example.com')
        assert self.get_claims() == []

    def test_makes_a_claim_if_asked_to(self):
        alice = self.make_participant('alice')
        foo = self.make_package()
        with self.db.get_cursor() as c:
            alice.get_email_verification_link(c, 'alice@example.com', foo)
        assert self.get_claims() == ['foo']

    def test_can_make_two_claims(self):
        alice = self.make_participant('alice')
        foo = self.make_package()
        bar = self.make_package(name='bar')
        with self.db.get_cursor() as c:
            alice.get_email_verification_link(c, 'alice@example.com', foo, bar)
        assert self.get_claims() == ['bar', 'foo']

    def test_will_happily_make_competing_claims(self):
        foo = self.make_package()
        with self.db.get_cursor() as c:
            self.make_participant('alice').get_email_verification_link(c, 'alice@example.com', foo)
        with self.db.get_cursor() as c:
            self.make_participant('bob').get_email_verification_link(c, 'bob@example.com', foo)
        assert self.get_claims() == ['foo', 'foo']

    def test_adds_events(self):
        foo = self.make_package()
        with self.db.get_cursor() as c:
            self.make_participant('alice').get_email_verification_link(c, 'alice@example.com', foo)
        events = [e.payload['action'] for e in self.db.all('select * from events order by id')]
        assert events == ['add', 'start-claim']


class VerificationBase(Alice):

    def check(self, *package_names, **kw):
        packages = [self.make_package(name=n) for n in package_names]
        self.alice.start_email_verification('alice@example.com', *packages)
        message = self.get_last_email()
        return message['subject'], message['body_html'], message['body_text']

    def preverify(self, address='alice@example.com'):
        self.alice.start_email_verification(address)
        nonce = self.alice.get_email(address).nonce
        self.alice.finish_email_verification(address, nonce)


class VerificationMessage(VerificationBase):

    def check(self, *a, **kw):
        subject, html, text = VerificationBase.check(self, *a, **kw)
        assert subject == 'Connect to alice on Gratipay?'
        return html, text

    def test_chokes_on_just_verified_address(self):
        self.preverify()
        raises(EmailAlreadyVerified, self.check)

    def test_handles_just_address(self):
        html, text = self.check()
        assert ' connect <b>alice@example.com</b> to ' in html
        assert ' connect alice@example.com to ' in text

    # NB: The next two also exercise skipping the verification notice when
    # sending package verification to an already-verified address, since the
    # last email sent would be the verification notice if we didn't skip it.

    def test_handles_verified_address_and_one_package(self):
        self.preverify()
        html, text = self.check('foo')
        assert ' connect the <b>foo</b> npm package ' in html
        assert ' connect the foo npm package ' in text

    def test_handles_verified_address_and_multiple_packages(self):
        self.preverify()
        html, text = self.check('foo', 'bar')
        assert ' connect 2 npm packages ' in html
        assert ' connect 2 npm packages ' in text

    def test_handles_unverified_address_and_one_package(self):
        html, text = self.check('foo')
        assert ' <b>alice@example.com</b> and the <b>foo</b> npm package ' in html
        assert ' alice@example.com and the foo npm package ' in text

    def test_handles_unverified_address_and_multiple_packages(self):
        html, text = self.check('foo', 'bar')
        assert ' <b>alice@example.com</b> and 2 npm packages ' in html
        assert ' alice@example.com and 2 npm packages ' in text


class VerificationNotice(VerificationBase):

    def setUp(self):
        VerificationBase.setUp(self)
        self.preverify('alice@gratipay.com')

    def check(self, *a, **kw):
        subject, html, text = VerificationBase.check(self, *a, **kw)
        assert subject == 'New activity on your account'
        assert ' notification sent to <b>alice@gratipay.com</b> because' in html
        assert ' notification sent to alice@gratipay.com because' in text
        return html, text

    def test_sends_notice_for_new_address(self):
        html, text = self.check()
        assert ' connecting <b>alice@example.com</b> to ' in html
        assert ' connecting alice@example.com to ' in text

    def test_sends_notice_for_verified_address_and_one_package(self):
        self.preverify()
        html, text = self.check('foo')
        assert ' connecting the <b>foo</b> npm package ' in html
        assert ' connecting the foo npm package to ' in text

    def test_sends_notice_for_verified_address_and_multiple_packages(self):
        self.preverify()
        html, text = self.check('foo', 'bar')
        assert ' connecting 2 npm packages ' in html
        assert ' connecting 2 npm packages ' in text

    def test_sends_notice_for_unverified_address_and_one_package(self):
        html, text = self.check('foo')
        assert ' connecting <b>alice@example.com</b> and the <b>foo</b> npm package ' in html
        assert ' connecting alice@example.com and the foo npm package ' in text

    def test_sends_notice_for_unverified_address_and_multiple_packages(self):
        html, text = self.check('foo', 'bar')
        assert ' connecting <b>alice@example.com</b> and 2 npm packages ' in html
        assert ' connecting alice@example.com and 2 npm packages ' in text


class PackageLinking(VerificationBase):

    address = 'alice@example.com'

    def start(self, address, *package_names):
        packages = [self.make_package(name=name, emails=[address]) for name in package_names]
        self.alice.start_email_verification(address, *packages)
        return self.alice.get_email(address).nonce

    @mock.patch('gratipay.project_review_process.ConsolePoster.post')
    def check(self, *package_names):
        package_names, post = package_names[:-1], package_names[-1]
        post.return_value = 'some-github-url'

        nonce = self.start(self.address, *package_names)
        result = self.alice.finish_email_verification(self.address, nonce)

        # email?
        packages = [Package.from_names(NPM, name) for name in package_names]
        assert result == (_email.VERIFICATION_SUCCEEDED, packages, True if packages else None)
        assert self.alice.email_address == P('alice').email_address == self.address

        # database?
        for name in package_names:
            package = Package.from_names(NPM, name)
            assert package.team.package == package
            assert package.team.review_url == 'some-github-url'

        # GitHub issue?
        npackages = len(package_names)
        if npackages == 0:
            assert not post.called
        else:
            assert post.call_count == 1
            posted = json.loads(post.mock_calls[0][1][0])
            if npackages == 1:
                assert posted['title'] == 'foo'
                assert 'for at least a week' in posted['body']
            else:
                assert posted['title'] == 'bar and foo'
                assert 'for at least a week' in posted['body']
            assert self.db.all('select review_url from teams') == ['some-github-url'] * npackages


    def test_preverify_preverifies(self):
        assert self.alice.email_address is None
        self.preverify()
        assert self.alice.email_address == self.address


    def test_unverified_address_and_no_packages_succeeds(self):
        self.check()

    def test_unverified_address_and_one_package_succeeds(self):
        self.check('foo')

    def test_unverified_address_and_multiple_packages_succeeds(self):
        self.check('bar', 'foo')

    def test_verified_address_and_no_packages_is_a_no_go(self):
        self.preverify()
        raises(EmailAlreadyVerified, self.check)

    def test_verified_address_and_one_package_succeeds(self):
        self.preverify()
        self.check('foo')

    def test_verified_address_and_multiple_packages_succeeds(self):
        self.preverify()
        self.check('bar', 'foo')


    def test_bob_cannot_steal_a_package_claim_from_alice(self):
        foo = self.make_package()
        self.alice.start_email_verification(self.address, foo)
        nonce = self.alice.get_email(self.address).nonce

        # u so bad bob!
        bob = self.make_participant('bob', claimed_time='now')
        bob.start_email_verification(self.address, foo)
        result = bob.finish_email_verification(self.address, nonce)  # using alice's nonce, even!
        assert result == (_email.VERIFICATION_FAILED, None, None)
        assert len(bob.get_teams()) == 0

        result = self.alice.finish_email_verification(self.address, nonce)
        assert result == (_email.VERIFICATION_SUCCEEDED, [foo], True)
        teams = self.alice.get_teams()
        assert len(teams) == 1
        assert teams[0].package == foo


    def test_while_we_are_at_it_that_packages_have_unique_teams_that_survive_comparison(self):
        self.test_verified_address_and_multiple_packages_succeeds()

        foo = Package.from_names('npm', 'foo')
        bar = Package.from_names('npm', 'bar')

        assert foo.team == foo.team
        assert bar.team == bar.team
        assert foo.team != bar.team


    def test_finishing_email_verification_with_preexisting_paypal_doesnt_update_paypal(self):
        self.add_and_verify_email(self.alice, self.address)
        self.alice.set_paypal_address(self.address)
        nonce = self.start(self.address, 'foo')
        result = self.alice.finish_email_verification(self.address, nonce)
        foo = Package.from_names('npm', 'foo')
        assert result == (_email.VERIFICATION_SUCCEEDED, [foo], False)


    def test_deleting_package_removes_open_claims(self):
        self.add_and_verify_email(self.alice, self.address)
        self.alice.set_paypal_address(self.address)
        self.start(self.address, 'foo')
        _load = lambda: self.db.one('select * from claims')
        assert _load() is not None
        Package.from_names('npm', 'foo').delete()
        assert _load() is None


    def test_finishing_email_verification_is_thread_safe(self):
        foo = self.make_package()
        self.alice.start_email_verification(self.address, foo)
        nonce = self.alice.get_email(self.address).nonce

        results = {}
        def finish():
            key = threading.current_thread().ident
            results[key] = self.alice.finish_email_verification(self.address, nonce)

        def t():
            t = threading.Thread(target=finish)
            t.daemon = True
            return t

        go = Queue.Queue()
        def monkey(self, *a, **kw):
            team = old_get_or_create_linked_team(self, *a, **kw)
            go.get()
            return team
        old_get_or_create_linked_team = Package.get_or_create_linked_team
        Package.get_or_create_linked_team = monkey

        try:
            a, b = t(), t()
            a.start()
            b.start()
            go.put('')
            go.put('')
            b.join()
            a.join()
        finally:
            Package.get_or_create_linked_team = old_get_or_create_linked_team

        assert results[a.ident] == (_email.VERIFICATION_SUCCEEDED, [foo], True)
        assert results[b.ident] == (_email.VERIFICATION_REDUNDANT, None, None)
