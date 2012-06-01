import unittest
from samurai.message import Message

class TestMessage(unittest.TestCase):
    def test_transaction_success(self):
        message = Message(subclass='info',
                          context='processor.transaction',
                          key='success')
        self.assertEqual(message.description,
                         'The transaction was successful.')

    def test_transaction_declined(self):
        message = Message(subclass='error',
                          context='processor.transaction',
                          key='declined')
        self.assertEqual(message.description,
                         'The card was declined.')

    def test_issuer_call(self):
        message = Message(subclass='error',
                          context='processor.issuer',
                          key='call')
        self.assertEqual(message.description,
                         'Call the card issuer for further instructions.')

    def test_issuer_unavailable(self):
        message = Message(subclass='error',
                          context='processor.issuer',
                          key='unavailable')
        self.assertEqual(message.description,
                         'The authorization did not respond within the alloted time.')

    def test_card_invalid(self):
        message = Message(subclass='error',
                          context='input.card_number',
                          key='invalid')
        self.assertEqual(message.description,
                         'The card number was invalid.')

    def test_expiry_month_invalid(self):
        message = Message(subclass='error',
                          context='input.expiry_month',
                          key='invalid')
        self.assertEqual(message.description,
                         'The expiration date month was invalid, or prior to today.')

    def test_expiry_year_invalid(self):
        message = Message(subclass='error',
                          context='input.expiry_year',
                          key='invalid')
        self.assertEqual(message.description,
                         'The expiration date year was invalid, or prior to today.')

    def test_amount_invalid(self):
        message = Message(subclass='error',
                          context='input.amount',
                          key='invalid')
        self.assertEqual(message.description,
                         'The transaction amount was invalid.')

    def test_insufficient_funds(self):
        message = Message(subclass='error',
                          context='processor.transaction',
                          key='declined_insufficient_funds')
        self.assertEqual(message.description,
                         'The transaction was declined due to insufficient funds.')


if __name__ == '__main__':
    unittest.main()
