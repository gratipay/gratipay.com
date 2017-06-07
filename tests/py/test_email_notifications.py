from gratipay.testing import Harness
from gratipay.models.participant import Participant


class Tests(Harness):

    def test_email_notifications_can_set_notification_prefs(self):
        alice = self.make_participant('alice', claimed_time='now')
        assert alice.notify_charge == 3
        self.client.POST( '/~alice/emails/notifications.json'
                        , data={'toggle': 'notify_charge'}
                        , auth_as='alice'
                         )
        assert Participant.from_username('alice').notify_charge == 2
