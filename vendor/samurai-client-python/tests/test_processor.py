import unittest
import test_helper
from samurai.processor import Processor
import samurai.config as config

class TestProcessor(unittest.TestCase):
    def setUp(self):
        self.pm = test_helper.default_payment_method()

    def test_purchase(self):
        token = self.pm.payment_method_token
        trans = Processor.purchase(token, 10.0)
        self.assertTrue(trans.success)
        self.assertEquals(trans.errors, [])

    def test_authorize(self):
        token = self.pm.payment_method_token
        trans = Processor.authorize(token, 10.0)
        self.assertTrue(trans.success)
        self.assertEquals(trans.errors, [])

    def test_purchase_failure(self):
        token = self.pm.payment_method_token
        trans = Processor.purchase(token, 10.02)
        errors = [{'context': 'processor.transaction', 'key': 'declined', 'subclass': 'error'}]
        self.assertEquals(trans.errors, errors)

    def test_authorize_failure(self):
        token = self.pm.payment_method_token
        trans = Processor.authorize(token, 10.02)
        errors = [{'context': 'processor.transaction', 'key': 'declined', 'subclass': 'error'}]
        self.assertEquals(trans.errors, errors)

if __name__ == '__main__':
    unittest.main()
