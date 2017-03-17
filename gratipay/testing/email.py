# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import mock

from gratipay.testing import Harness


class _AbstractEmailHarness(Harness):

    def _get_last_email(self):
        raise NotImplementedError

    def count_email_messages():
        raise NotImplementedError

    def get_last_email(self):
        """Flatten the SES format for easier test writing.
        """
        message = self._get_last_email()
        return {
            'from': message['Source'],
            'to': message['Destination']['ToAddresses'][0],
            'subject': message['Message']['Subject']['Data'],
            'body_text': message['Message']['Body']['Text']['Data'],
            'body_html': message['Message']['Body']['Html']['Data']
        }


class QueuedEmailHarness(_AbstractEmailHarness):
    """An email harness that pulls from the ``email_queue`` table.
    """

    def _get_last_email(self):
        rec = self.db.one('SELECT * FROM email_queue ORDER BY id DESC LIMIT 1')
        return self.app.email_queue._prepare_email_message_for_ses(rec)

    def count_email_messages(self):
        return self.db.one('SELECT count(*) FROM email_queue')


class SentEmailHarness(_AbstractEmailHarness):
    """An email harness that mocks ``_mailer.send_email`` to ``get_last_email``
    post-queue.
    """

    def setUp(self):
        Harness.setUp(self)
        self.mailer_patcher = mock.patch.object(self.app.email_queue._mailer, 'send_email')
        self.mailer = self.mailer_patcher.start()
        self.addCleanup(self.mailer_patcher.stop)
        sleep_patcher = mock.patch('gratipay.application.email.sleep')
        sleep_patcher.start()
        self.addCleanup(sleep_patcher.stop)

    def _get_last_email(self):
        return self.mailer.call_args[1]

    def count_email_messages(self):
        return self.mailer.call_count
