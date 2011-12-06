import unittest
import test_helper
from samurai.payment_method import PaymentMethod

class TestPaymentMethod(unittest.TestCase):
    def setUp(self):
        self.pm = PaymentMethod.create('4242424242424242',
                                       '133', '07', '12')

    def test_create(self):
        assert self.pm.is_sensitive_data_valid


    def test_create_failure(self):
        pm = PaymentMethod.create('4343434343434343', '133', '07', '12')
        assert not pm.is_sensitive_data_valid

        errors = [{'context': 'input.card_number',
                   'key': 'failed_checksum',
                   'subclass': 'error'}]
        assert pm.errors == errors

    def test_update(self):
        pm = self.pm.update(first_name='dummy')
        assert pm.first_name == 'dummy'

    def test_retain(self):
        pm = self.pm.retain()
        assert pm.is_retained

    def test_redact(self):
        pm = self.pm.redact()
        assert pm.is_redacted

if __name__ == '__main__':
    unittest.main()
