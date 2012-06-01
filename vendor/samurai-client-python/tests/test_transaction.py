import unittest
import test_helper
from samurai.processor import Processor
import samurai.config as config
from random import randint

class TestTransaction(unittest.TestCase):
    def setUp(self):
        self.pm = test_helper.default_payment_method()
        self.rand = randint(100, 999)
        self.auth = Processor.authorize(self.pm.payment_method_token, 100.0)
        self.purchase = Processor.purchase(self.pm.payment_method_token, 100.0)

    def test_capture_should_be_successful(self):
        capture = self.auth.capture()
        self.assertTrue(capture.success)
        self.assertEquals(capture.error_messages, [])

    def test_capture_should_be_successful_for_full_amount(self):
        capture = self.auth.capture(100.0)
        self.assertTrue(capture.success)
        self.assertEquals(capture.error_messages, [])

    def test_capture_should_be_successful_for_partial_amount(self):
        capture = self.auth.capture(50.0)
        self.assertTrue(capture.success)
        self.assertEquals(capture.error_messages, [])

    def test_capture_should_return_processor_transaction_invalid_with_declined_auth(self):
        auth = Processor.authorize(self.pm.payment_method_token, 100.02)  # declined auth
        capture = auth.capture()
        self.assertFalse(capture.success)
        err = {'context': 'processor.transaction', 'key': 'not_allowed', 'subclass': 'error'}
        self.assertIn(err, capture.error_messages)

    def test_capture_should_return_processor_transaction_declined(self):
        auth = Processor.authorize(self.pm.payment_method_token, 100.00)
        capture = auth.capture(100.02)
        self.assertFalse(capture.success)
        err = {'context': 'processor.transaction', 'key': 'declined', 'subclass': 'error'}
        self.assertIn(err, capture.error_messages)
        self.assertIn('The card was declined.', capture.errors['processor.transaction'])

    def test_capture_should_return_input_amount_invalid(self):
        auth = Processor.authorize(self.pm.payment_method_token, 100.00)
        capture = auth.capture(100.10)
        self.assertFalse(capture.success)
        err = {'context': 'input.amount', 'key': 'invalid', 'subclass': 'error'}
        self.assertIn(err, capture.error_messages)
        self.assertIn('The transaction amount was invalid.', capture.errors['input.amount'])

    def test_reverse_capture_should_be_successful(self):
        reverse = self.purchase.reverse()
        self.assertTrue(reverse.success)

    def test_reverse_capture_should_be_successful_for_full_amount(self):
        reverse = self.purchase.reverse(100.0)
        self.assertTrue(reverse.success)

    def test_reverse_capture_should_be_successful_for_partial_amount(self):
        reverse = self.purchase.reverse(50.0)
        self.assertTrue(reverse.success)

    def test_reverse_authorize_should_be_successful(self):
        reverse = self.auth.reverse()
        self.assertTrue(reverse.success)

    def test_reverse_failure_should_return_input_amount_invalid(self):
        reverse = self.purchase.reverse(100.10)
        self.assertFalse(reverse.success)
        err = {'context': 'input.amount', 'key': 'invalid', 'subclass': 'error'}
        self.assertIn(err, reverse.error_messages)
        self.assertIn('The transaction amount was invalid.', reverse.errors['input.amount'])

    def test_credit_capture_should_be_successful(self):
        credit = self.purchase.credit()
        self.assertTrue(credit.success)

    def test_credit_capture_should_be_successful_for_full_amount(self):
        credit = self.purchase.credit(100.0)
        self.assertTrue(credit.success)

    def test_credit_capture_should_be_successful_for_partial_amount(self):
        credit = self.purchase.credit(50.0)
        self.assertTrue(credit.success)

    def test_credit_authorize_should_be_successful(self):
        credit = self.auth.credit()
        self.assertTrue(credit.success)

    def test_credit_failure_should_return_input_amount_invalid(self):
        credit = self.purchase.credit(100.10)
        self.assertFalse(credit.success)
        err = {'context': 'input.amount', 'key': 'invalid', 'subclass': 'error'}
        self.assertIn(err, credit.error_messages)
        self.assertIn('The transaction amount was invalid.', credit.errors['input.amount'])

    def test_void_capture_should_be_successful(self):
        void = self.purchase.void()
        self.assertTrue(void.success)

    def test_void_authorize_should_be_successful(self):
        void = self.auth.void()
        self.assertTrue(void.success)

if __name__ == '__main__':
    unittest.main()
