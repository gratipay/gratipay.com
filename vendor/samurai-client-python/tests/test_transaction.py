import unittest
import test_helper
from samurai.processor import Processor
import samurai.config as config

class TestTransaction(unittest.TestCase):
    def setUp(self):
        self.pm = test_helper.default_payment_method()

    def test_authorize_capture(self):
        auth = Processor.authorize(self.pm.payment_method_token, 10.0)      
        trans = auth.capture(10.0)
        self.assertTrue(trans.success)
        self.assertEquals(trans.errors, [])

    def test_authorize_partial_capture(self):
        auth = Processor.authorize(self.pm.payment_method_token, 10.0)      
        trans = auth.capture(8.0)
        self.assertTrue(trans.success)
        self.assertEquals(trans.amount, '8.0')
        self.assertEquals(trans.errors, [])

    def test_authorize_capture_failed(self):
        auth = Processor.authorize(self.pm.payment_method_token, 10.0)      
        trans = auth.capture(10.02)
        self.assertFalse(trans.success)
        errors = [{'context': 'processor.transaction', 'key': 'declined', 'subclass': 'error'}]
        self.assertEquals(trans.errors, errors)

    def test_authorize_void(self):
        auth = Processor.authorize(self.pm.payment_method_token, 10.0)      
        trans = auth.void()
        self.assertTrue(trans.success)
        self.assertEquals(trans.errors, [])

    def test_authorize_capture_reverse(self):
        auth = Processor.authorize(self.pm.payment_method_token, 10.0)      
        capture = auth.capture(10.0)
        trans = capture.reverse()        
        self.assertTrue(trans.success)
        self.assertEquals(trans.errors, [])

    def test_purchase_reverse(self):
        purchase = Processor.purchase(self.pm.payment_method_token, 10.0)      
        trans = purchase.reverse()
        self.assertTrue(trans.success)
        self.assertEquals(trans.errors, [])

    def test_purchase_partial_reverse(self):
        purchase = Processor.purchase(self.pm.payment_method_token, 10.0)      
        trans = purchase.reverse(5.0)
        self.assertTrue(trans.success)
        self.assertEquals(trans.errors, [])
        self.assertEquals(trans.amount, '5.0')

if __name__ == '__main__':
    unittest.main()
