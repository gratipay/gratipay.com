import mock

from gratipay.models.participant import Participant
from gratipay.testing import Harness


class EmailHarness(Harness):

    def setUp(self):
        Harness.setUp(self)
        self.mailer_patcher = mock.patch.object(Participant._mailer, 'send_email')
        self.mailer = self.mailer_patcher.start()
        self.addCleanup(self.mailer_patcher.stop)
        sleep_patcher = mock.patch('gratipay.models.participant.sleep')
        sleep_patcher.start()
        self.addCleanup(sleep_patcher.stop)

    def get_last_email(self):
        args = self.mailer.call_args[1]

        return {
            'from': args['Source'],
            'to': args['Destination']['ToAddresses'][0],
            'subject': args['Message']['Subject']['Data'],
            'body_text': args['Message']['Body']['Text']['Data'],
            'body_html': args['Message']['Body']['Html']['Data']
        }
