import unittest
import test_helper
from samurai.processor import Processor
import samurai.config as config
from random import randint

class TestProcessor(unittest.TestCase):
    def setUp(self):
        self.pm = test_helper.default_payment_method()
        self.rand = randint(100, 999)

    def test_should_return_the_default_processor(self):
        processor = Processor.the_processor
        self.assertNotEqual(processor, None)
        self.assertEqual(processor.processor_token, config.processor_token)

    def test_should_return_a_processor(self):
        processor = Processor('abc123')
        self.assertNotEqual(processor, None)
        self.assertEqual(processor.processor_token, 'abc123')

    def test_purchase_should_be_successful(self):
        options = {'description':'description',
                   'descriptor_name':'descriptor_name',
                   'descriptor_phone':'descriptor_phone',
                   'custom':'custom',
                   'billing_reference':'ABC123%s' % self.rand,
                   'customer_reference':'Customer (123)'}
        token = self.pm.payment_method_token
        purchase = Processor.purchase(token, 10.0, None, **options)
        self.assertTrue(purchase.success)
        self.assertEquals(purchase.error_messages, [])
        self.assertEqual(purchase.description, 'description')
        self.assertEqual(purchase.descriptor_name, 'descriptor_name')
        self.assertEqual(purchase.descriptor_phone, 'descriptor_phone')
        self.assertEqual(purchase.custom, 'custom')
        self.assertEqual(purchase.billing_reference, 'ABC123%s' % self.rand)
        self.assertEqual(purchase.customer_reference, 'Customer (123)')

    def test_purchase_should_return_processor_transaction_declined(self):
        token = self.pm.payment_method_token
        purchase = Processor.purchase(token,
                                      1.02,
                                      billing_reference=self.rand)
        self.assertFalse(purchase.success)
        err = {'context': 'processor.transaction', 'key': 'declined', 'subclass': 'error'}
        self.assertIn(err, purchase.error_messages)
        self.assertIn('The card was declined.' , purchase.errors['processor.transaction'])

    def test_purchase_should_return_input_amount_invalid(self):
        token = self.pm.payment_method_token
        purchase = Processor.purchase(token,
                                      1.10,
                                      billing_reference=self.rand)
        self.assertFalse(purchase.success)
        err = {'context': 'input.amount', 'key': 'invalid', 'subclass': 'error'}
        self.assertIn(err, purchase.error_messages)
        self.assertIn('The transaction amount was invalid.', purchase.errors['input.amount'])

    def test_purchase_should_return_payment_method_errors_on_blank_pm(self):
        data = {
            'custom' : '',
            'first_name' : '',
            'last_name' : '',
            'address_1' : '',
            'address_2' : '',
            'city' : '',
            'state' : '',
            'zip' : '',
            'card_number' : '',
            'cvv' : '',
            'expiry_month' : '05',
            'expiry_year' : '2014',
          }
        token = test_helper.default_payment_method(data).payment_method_token
        purchase = Processor.purchase(token, 1.00)
        self.assertFalse(purchase.success)
        self.assertIn({'context': 'input.card_number', 'key': 'not_numeric', 'subclass': 'error'}, purchase.error_messages)
        self.assertIn({'context': 'input.card_number', 'key': 'too_short', 'subclass': 'error'}, purchase.error_messages)
        self.assertIn({'context': 'input.card_number', 'key': 'is_blank', 'subclass': 'error'}, purchase.error_messages)

    def test_purchase_should_return_invalid_sandbox_card_error(self):
        data = {
            'custom' : '',
            'first_name' : '',
            'last_name' : '',
            'address_1' : '',
            'address_2' : '',
            'city' : '',
            'state' : '',
            'zip' : '10101',
            'card_number' : '5256486068715680',
            'cvv' : '111',
            'expiry_month' : '05',
            'expiry_year' : '2014',
          }
        token = test_helper.default_payment_method(data).payment_method_token
        purchase = Processor.purchase(token, 1.00)
        self.assertIn({'context': 'system.general', 'key': 'default', 'subclass': 'error', 'text': 'Invalid Sandbox Card Number. For more information, see: https://samurai.feefighters.com/developers/sandbox'}, purchase.error_messages)

    def test_cvv_should_return_processor_cvv_result_code_M(self):
        token = test_helper.default_payment_method({'cvv':'111'}).payment_method_token
        purchase = Processor.purchase(token,
                                      1.00,
                                      billing_reference=self.rand)
        self.assertTrue(purchase.success)
        self.assertEqual(purchase.processor_response['cvv_result_code'], 'M')

    def test_cvv_should_return_processor_cvv_result_code_N(self):
        token = test_helper.default_payment_method({'cvv':'222'}).payment_method_token
        purchase = Processor.purchase(token,
                                      1.00,
                                      billing_reference=self.rand)
        self.assertTrue(purchase.success)
        self.assertEqual(purchase.processor_response['cvv_result_code'], 'N')

    def test_avs_should_return_processor_avs_result_code_Y(self):
        token = test_helper.default_payment_method({'address_1':'1000 1st Av',
                                                    'address_2':'',
                                                    'zip':'10101'}).payment_method_token
        purchase = Processor.purchase(token,
                                      1.00,
                                      billing_reference=self.rand)
        self.assertTrue(purchase.success)
        self.assertEqual(purchase.processor_response['avs_result_code'],'Y')

    # This test returns X in place of Z, confirm with Josh.
    def test_avs_should_return_processor_avs_result_code_Z(self):
        token = test_helper.default_payment_method({'address_1':'',
                                                    'address_2':'',
                                                    'zip':'10101'}).payment_method_token
        purchase = Processor.purchase(token,
                                      1.00,
                                      billing_reference=self.rand)
        self.assertTrue(purchase.success)
        self.assertEqual(purchase.processor_response['avs_result_code'], 'Z')

    def test_should_return_processor_avs_result_code_N(self):
        token = test_helper.default_payment_method({'address_1':'123 Main St',
                                                   'address_2':'',
                                                   'zip':'60610'}).payment_method_token
        purchase = Processor.purchase(token,
                                      1.00,
                                      billing_reference=self.rand)
        self.assertTrue(purchase.success)
        self.assertEqual(purchase.processor_response['avs_result_code'], 'N')

    def test_authorize_should_be_successful(self):
        options = {'description':'description',
                   'descriptor_name':'descriptor_name',
                   'descriptor_phone':'descriptor_phone',
                   'custom':'custom',
                   'billing_reference':'ABC123%s' % self.rand,
                   'customer_reference':'Customer (123)'}
        token = self.pm.payment_method_token
        purchase = Processor.authorize(token, 100.0, None, **options)
        self.assertTrue(purchase.success)
        self.assertEquals(purchase.error_messages, [])
        self.assertEqual(purchase.description, 'description')
        self.assertEqual(purchase.descriptor_name, 'descriptor_name')
        self.assertEqual(purchase.descriptor_phone, 'descriptor_phone')
        self.assertEqual(purchase.custom, 'custom')
        self.assertEqual(purchase.billing_reference, 'ABC123%s' % self.rand)
        self.assertEqual(purchase.customer_reference, 'Customer (123)')

    def test_authorize_should_return_processor_transaction_declined(self):
        token = self.pm.payment_method_token
        purchase = Processor.authorize(token,
                                      1.02,
                                      billing_reference=self.rand)
        self.assertFalse(purchase.success)
        err = {'context': 'processor.transaction', 'key': 'declined', 'subclass': 'error'}
        self.assertIn(err, purchase.error_messages)
        self.assertIn('The card was declined.' , purchase.errors['processor.transaction'])

    def test_authorize_should_return_input_amount_invalid(self):
        token = self.pm.payment_method_token
        purchase = Processor.authorize(token,
                                      1.10,
                                      billing_reference=self.rand)
        self.assertFalse(purchase.success)
        err = {'context': 'input.amount', 'key': 'invalid', 'subclass': 'error'}
        self.assertIn(err, purchase.error_messages)
        self.assertIn('The transaction amount was invalid.', purchase.errors['input.amount'])

    def test_authorize_should_return_processor_cvv_result_code_M(self):
        token = test_helper.default_payment_method({'cvv':'111'}).payment_method_token
        purchase = Processor.authorize(token,
                                      1.00,
                                      billing_reference=self.rand)
        self.assertTrue(purchase.success)
        self.assertEqual(purchase.processor_response['cvv_result_code'], 'M')

    def test_authorize_should_return_processor_cvv_result_code_N(self):
        token = test_helper.default_payment_method({'cvv':'222'}).payment_method_token
        purchase = Processor.authorize(token,
                                      1.00,
                                      billing_reference=self.rand)
        self.assertTrue(purchase.success)
        self.assertEqual(purchase.processor_response['cvv_result_code'], 'N')

    def test_authorize_should_return_processor_avs_result_code_Y(self):
        token = test_helper.default_payment_method({'address_1':'1000 1st Av',
                                                    'address_2':'',
                                                    'zip':'10101'}).payment_method_token
        purchase = Processor.authorize(token,
                                      1.00,
                                      billing_reference=self.rand)
        self.assertTrue(purchase.success)
        self.assertEqual(purchase.processor_response['avs_result_code'], 'Y')

    def test_authorize_should_return_processor_avs_result_code_Z(self):
        token = test_helper.default_payment_method({'address_1':'',
                                                    'address_2':'',
                                                    'zip':'10101'}).payment_method_token
        purchase = Processor.authorize(token,
                                      1.00,
                                      billing_reference=self.rand)
        self.assertTrue(purchase.success)
        self.assertEqual(purchase.processor_response['avs_result_code'], 'Z')

    def test_authorize_should_return_processor_avs_result_code_N(self):
        token = test_helper.default_payment_method({'address_1':'123 Main St',
                                                   'address_2':'',
                                                   'zip':'60610'}).payment_method_token
        purchase = Processor.authorize(token,
                                      1.00,
                                      billing_reference=self.rand)
        self.assertTrue(purchase.success)
        self.assertEqual(purchase.processor_response['avs_result_code'], 'N')

if __name__ == '__main__':
    unittest.main()
