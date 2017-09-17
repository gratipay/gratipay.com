# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing import Harness


class _AbstractEmailHarness(Harness):

    def setUp(self):
        Harness.setUp(self)
        self.__sleep_for = self.app.email_queue.sleep_for
        self.app.email_queue.sleep_for = 0

    def tearDown(self):
        Harness.tearDown(self)
        self.app.email_queue.sleep_for = self.__sleep_for

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
    """An email harness that pulls from the ``email_messages`` table.
    """

    _SELECT = 'SELECT * FROM email_messages WHERE result is null ORDER BY ctime DESC LIMIT 1'

    def _get_last_email(self):
        rec = self.db.one(self._SELECT)
        return self.app.email_queue._prepare_email_message_for_ses(rec)

    def count_email_messages(self):
        return self.db.one('SELECT count(*) FROM email_messages WHERE result is null')

    def pop_email_message(self):
        """Same as get_last_email but also marks as sent in the db.
        """
        out = self.get_last_email()
        rec = self.db.one(self._SELECT)
        self.app.email_queue._store_result(rec.id, '', 'deadbeef')
        return out


class SentEmailHarness(_AbstractEmailHarness):
    """An email harness that patches ``_mailer.send_email`` to ``get_last_email``
    after running through the email queue machinery.
    """

    def setUp(self):
        _AbstractEmailHarness.setUp(self)
        self.__messages = []

        def send_email(**message):
            self.__messages.append(message)
            return {'MessageId': 'deadbeef'}

        self.__send_email = self.app.email_queue._mailer.send_email
        self.app.email_queue._mailer.send_email = send_email

    def tearDown(self):
        self.app.email_queue._mailer.send_email = self.__send_email
        _AbstractEmailHarness.tearDown(self)

    def _get_last_email(self):
        return self.__messages[-1]

    def count_email_messages(self):
        return len(self.__messages)
