import unittest
import test_helper
from samurai.payment_method import PaymentMethod

params = {
    'first_name'  : "FirstName",
    'last_name'   : "LastName",
    'address_1'   : "123 Main St.",
    'address_2'   : "Apt #3",
    'city'        : "Chicago",
    'state'       : "IL",
    'zip'         : "10101",
    'card_number' : "4111-1111-1111-1111",
    'cvv'         : "123",
    'expiry_month': '03',
    'expiry_year' : "2015",
}

paramsx = {
    'first_name'  : "FirstNameX",
    'last_name'   : "LastNameX",
    'address_1'   : "123 Main St.X",
    'address_2'   : "Apt #3X",
    'city'        : "ChicagoX",
    'state'       : "IL",
    'zip'         : "10101",
    'card_number' : "5454-5454-5454-5454",
    'cvv'         : "456",
    'expiry_month': '05',
    'expiry_year' : "2016",
}

class TestPaymentMethod(unittest.TestCase):
    def setUp(self):
        self.pm = PaymentMethod.create(**params)

    #
    # Test create
    #

    def test_create(self):
        self.assertTrue(self.pm.is_sensitive_data_valid)
        self.assertTrue(self.pm.is_expiration_valid)
        self.assertEqual(self.pm.first_name, params['first_name'])
        self.assertEqual(self.pm.last_name, params['last_name'])
        self.assertEqual(self.pm.address_1, params['address_1'])
        self.assertEqual(self.pm.address_2, params['address_2'])
        self.assertEqual(self.pm.city, params['city'])
        self.assertEqual(self.pm.state, params['state'])
        self.assertEqual(self.pm.zip, params['zip'])
        self.assertEqual(self.pm.last_four_digits, params['card_number'][-4:])
        self.assertEqual(self.pm.expiry_month, int(params['expiry_month']))
        self.assertEqual(self.pm.expiry_year, int(params['expiry_year']))

    #
    # Test failure on input.card_number
    #

    def test_should_fail_on_blank_card_number(self):
        params_tmp = params
        params_tmp['card_number'] =  ''
        pm = PaymentMethod.create(**params_tmp)
        self.assertFalse(pm.is_sensitive_data_valid)
        err = {'context': 'input.card_number', 'key': 'is_blank', 'subclass': 'error'}
        self.assertIn(err, pm.error_messages)
        self.assertIn('The card number was blank.', pm.errors['input.card_number'])

    def test_should_return_too_short_card_number(self):
        params_tmp = params
        params_tmp['card_number'] =  '4111-1'
        pm = PaymentMethod.create(**params_tmp)
        self.assertFalse(pm.is_sensitive_data_valid)
        err = {'context': 'input.card_number', 'key': 'too_short', 'subclass': 'error'}
        self.assertIn(err, pm.error_messages)
        self.assertIn('The card number was too short.', pm.errors['input.card_number'])

    def test_should_return_too_long_card_number(self):
        params_tmp = params
        params_tmp['card_number'] =  '4111-1111-1111-1111-11'
        pm = PaymentMethod.create(**params_tmp)
        self.assertFalse(pm.is_sensitive_data_valid)
        err = {'context': 'input.card_number', 'key': 'too_long', 'subclass': 'error'}
        self.assertIn(err, pm.error_messages)
        self.assertIn('The card number was too long.', pm.errors['input.card_number'])

    def test_should_return_failed_checksum_card_number(self):
        params_tmp = params
        params_tmp['card_number'] =  '4111-1111-1111-1234'
        pm = PaymentMethod.create(**params_tmp)
        self.assertFalse(pm.is_sensitive_data_valid)
        err = {'context': 'input.card_number', 'key': 'failed_checksum', 'subclass': 'error'}
        self.assertIn(err, pm.error_messages)
        self.assertIn('The card number was invalid.', pm.errors['input.card_number'])


    #
    # Test failure on input.cvv
    #

    def test_should_return_too_short_cvv(self):
        params_tmp = params
        params_tmp['cvv'] =  '1'
        pm = PaymentMethod.create(**params_tmp)
        self.assertFalse(pm.is_sensitive_data_valid)
        err = {'context': 'input.cvv', 'key': 'too_short', 'subclass': 'error'}
        self.assertIn(err, pm.error_messages)
        self.assertIn('The CVV was too short.', pm.errors['input.cvv'])

    def test_should_return_too_long_cvv(self):
        params_tmp = params
        params_tmp['cvv'] =  '1111111'
        pm = PaymentMethod.create(**params_tmp)
        self.assertFalse(pm.is_sensitive_data_valid)
        err = {'context': 'input.cvv', 'key': 'too_long', 'subclass': 'error'}
        self.assertIn(err, pm.error_messages)
        self.assertIn('The CVV was too long.', pm.errors['input.cvv'])

    def test_should_return_not_numeric_cvv(self):
        params_tmp = params
        params_tmp['cvv'] =  'abcd1'
        pm = PaymentMethod.create(**params_tmp)
        self.assertFalse(pm.is_sensitive_data_valid)
        err = {'context': 'input.cvv', 'key': 'not_numeric', 'subclass': 'error'}
        self.assertIn(err, pm.error_messages)
        self.assertIn('The CVV was invalid.', pm.errors['input.cvv'])

    #
    # Test failure on input.expiry_month
    #

    def test_should_return_is_blank_expiry_month(self):
        params_tmp = params
        params_tmp['expiry_month'] =  ''
        pm = PaymentMethod.create(**params_tmp)
        self.assertFalse(pm.is_sensitive_data_valid)
        self.assertFalse(pm.is_expiration_valid)
        err = {'context': 'input.expiry_month', 'key': 'is_blank', 'subclass': 'error'}
        self.assertIn(err, pm.error_messages)
        self.assertIn('The expiration month was blank.', pm.errors['input.expiry_month'])

    def test_should_return_is_invalid(self):
        params_tmp = params
        params_tmp['expiry_month'] =  'abcd'
        pm = PaymentMethod.create(**params_tmp)
        self.assertFalse(pm.is_sensitive_data_valid)
        self.assertFalse(pm.is_expiration_valid)
        err = {'context': 'input.expiry_month', 'key': 'is_invalid', 'subclass': 'error'}
        self.assertIn(err, pm.error_messages)
        self.assertIn('The expiration month was invalid.', pm.errors['input.expiry_month'])

    #
    # Test failure on input.expiry_year
    #

    def test_should_return_is_blank_expiry_year(self):
        params_tmp = params
        params_tmp['expiry_year'] =  ''
        pm = PaymentMethod.create(**params_tmp)
        self.assertFalse(pm.is_sensitive_data_valid)
        self.assertFalse(pm.is_expiration_valid)
        err = {'context': 'input.expiry_year', 'key': 'is_blank', 'subclass': 'error'}
        self.assertIn(err, pm.error_messages)
        self.assertIn('The expiration year was blank.', pm.errors['input.expiry_year'])

    def test_should_return_is_invalid_expiry_year(self):
        params_tmp = params
        params_tmp['expiry_year'] =  'abcd'
        pm = PaymentMethod.create(**params_tmp)
        self.assertFalse(pm.is_sensitive_data_valid)
        self.assertFalse(pm.is_expiration_valid)
        err = {'context': 'input.expiry_year', 'key': 'is_invalid', 'subclass': 'error'}
        self.assertIn(err, pm.error_messages)
        self.assertIn('The expiration year was invalid.', pm.errors['input.expiry_year'])

    #
    # S2SUpdate
    #

    def test_update(self):
        pm = self.pm.update(**paramsx)
        self.assertTrue(pm.is_sensitive_data_valid)
        self.assertTrue(pm.is_expiration_valid)
        self.assertEqual(pm.first_name, paramsx['first_name'])
        self.assertEqual(pm.last_name, paramsx['last_name'])
        self.assertEqual(pm.address_1, paramsx['address_1'])
        self.assertEqual(pm.address_2, paramsx['address_2'])
        self.assertEqual(pm.city, paramsx['city'])
        self.assertEqual(pm.state, paramsx['state'])
        self.assertEqual(pm.zip, paramsx['zip'])
        self.assertEqual(pm.last_four_digits, paramsx['card_number'][-4:])
        self.assertEqual(pm.expiry_month, int(paramsx['expiry_month']))
        self.assertEqual(pm.expiry_year, int(paramsx['expiry_year']))

    def test_update_should_be_successful_preserving_sensitive_data(self):
        params_tmp = paramsx
        params_tmp['card_number'] = '****************'
        params_tmp['cvv'] = '***'
        pm = PaymentMethod.create(**params)
        pm = pm.update(**paramsx)
        self.assertTrue(pm.is_expiration_valid)
        self.assertEqual(pm.first_name, params_tmp['first_name'])
        self.assertEqual(pm.last_name, params_tmp['last_name'])
        self.assertEqual(pm.address_1, params_tmp['address_1'])
        self.assertEqual(pm.address_2, params_tmp['address_2'])
        self.assertEqual(pm.city, params_tmp['city'])
        self.assertEqual(pm.state, params_tmp['state'])
        self.assertEqual(pm.zip, params_tmp['zip'])
        self.assertEqual(pm.last_four_digits, '1111')
        self.assertEqual(pm.expiry_month, int(params_tmp['expiry_month']))
        self.assertEqual(pm.expiry_year, int(params_tmp['expiry_year']))

    #
    # Test failure on input.card_number
    #

    def test_update_should_return_too_long_card_number(self):
        params_tmp = paramsx
        params_tmp['card_number'] =  '4111-1111-1111-1111-11'
        pm = self.pm.update(**params_tmp)
        self.assertFalse(pm.is_sensitive_data_valid)
        err = {'context': 'input.card_number', 'key': 'too_long', 'subclass': 'error'}
        self.assertIn(err, pm.error_messages)
        self.assertIn('The card number was too long.', pm.errors['input.card_number'])

    def test_update_should_return_too_short_card_number(self):
        pm = self.pm.update(card_number='4111-1')
        self.assertFalse(pm.is_sensitive_data_valid)
        err = {'context': 'input.card_number', 'key': 'too_short', 'subclass': 'error'}
        self.assertIn(err, pm.error_messages)
        self.assertIn('The card number was too short.', pm.errors['input.card_number'])

    def test_update_should_return_failed_checksum_card_number(self):
        params_tmp = paramsx
        params_tmp['card_number'] =  '4111-1111-1111-1234'
        pm = self.pm.update(**params_tmp)
        self.assertFalse(pm.is_sensitive_data_valid)
        err = {'context': 'input.card_number', 'key': 'failed_checksum', 'subclass': 'error'}
        self.assertIn(err, pm.error_messages)
        self.assertIn('The card number was invalid.', pm.errors['input.card_number'])


    #
    # Test failure on input.cvv
    #

    def test_update_should_return_too_short_cvv(self):
        params_tmp = paramsx
        params_tmp['cvv'] =  '1'
        pm = self.pm.update(**params_tmp)
        self.assertFalse(pm.is_sensitive_data_valid)
        err = {'context': 'input.cvv', 'key': 'too_short', 'subclass': 'error'}
        self.assertIn(err, pm.error_messages)
        self.assertIn('The CVV was too short.', pm.errors['input.cvv'])

    def test_update_should_return_too_long_cvv(self):
        params_tmp = paramsx
        params_tmp['cvv'] =  '1111111'
        pm = self.pm.update(**params_tmp)
        self.assertFalse(pm.is_sensitive_data_valid)
        err = {'context': 'input.cvv', 'key': 'too_long', 'subclass': 'error'}
        self.assertIn(err, pm.error_messages)
        self.assertIn('The CVV was too long.', pm.errors['input.cvv'])


    # returns too_short, should return not_numeric
    def test_update_should_return_not_numeric_cvv(self):
        params_tmp = paramsx
        params_tmp['cvv'] =  'abcd1'
        pm = self.pm.update(**params_tmp)
        self.assertFalse(pm.is_sensitive_data_valid)
        err = {'context': 'input.cvv', 'key': 'too_short', 'subclass': 'error'}
        self.assertIn(err, pm.error_messages)
        self.assertIn('The CVV was too short.', pm.errors['input.cvv'])

    #
    # Test failure on input.expiry_month
    #

    def test_update_should_return_is_blank_expiry_month(self):
        params_tmp = paramsx
        params_tmp['expiry_month'] =  ''
        pm = self.pm.update(**params_tmp)
        self.assertFalse(pm.is_sensitive_data_valid)
        self.assertFalse(pm.is_expiration_valid)
        err = {'context': 'input.expiry_month', 'key': 'is_blank', 'subclass': 'error'}
        self.assertIn(err, pm.error_messages)
        self.assertIn('The expiration month was blank.', pm.errors['input.expiry_month'])

    def test_update_should_return_is_invalid(self):
        params_tmp = paramsx
        params_tmp['expiry_month'] =  'abcd'
        pm = self.pm.update(**params_tmp)
        self.assertFalse(pm.is_sensitive_data_valid)
        self.assertFalse(pm.is_expiration_valid)
        err = {'context': 'input.expiry_month', 'key': 'is_invalid', 'subclass': 'error'}
        self.assertIn(err, pm.error_messages)
        self.assertIn('The expiration month was invalid.', pm.errors['input.expiry_month'])

    #
    # Test failure on input.expiry_year
    #

    def test_update_should_return_is_blank_expiry_year(self):
        params_tmp = paramsx
        params_tmp['expiry_year'] =  ''
        pm = self.pm.update(**params_tmp)
        self.assertFalse(pm.is_sensitive_data_valid)
        self.assertFalse(pm.is_expiration_valid)
        err = {'context': 'input.expiry_year', 'key': 'is_blank', 'subclass': 'error'}
        self.assertIn(err, pm.error_messages)
        self.assertIn('The expiration year was blank.', pm.errors['input.expiry_year'])

    def test_update_should_return_is_invalid_expiry_year(self):
        params_tmp = paramsx
        params_tmp['expiry_year'] =  'abcd'
        pm = self.pm.update(**params_tmp)
        self.assertFalse(pm.is_sensitive_data_valid)
        self.assertFalse(pm.is_expiration_valid)
        err = {'context': 'input.expiry_year', 'key': 'is_invalid', 'subclass': 'error'}
        self.assertIn(err, pm.error_messages)
        self.assertIn('The expiration year was invalid.', pm.errors['input.expiry_year'])

    #
    #find
    #

    def test_find_should_be_successful(self):
      pm = PaymentMethod.create(**params)
      token = pm.payment_method_token
      pm = PaymentMethod.find(token)
      self.assertTrue(self.pm.is_sensitive_data_valid)
      self.assertTrue(self.pm.is_expiration_valid)
      self.assertEqual(self.pm.first_name, params['first_name'])
      self.assertEqual(self.pm.last_name, params['last_name'])
      self.assertEqual(self.pm.address_1, params['address_1'])
      self.assertEqual(self.pm.address_2, params['address_2'])
      self.assertEqual(self.pm.city, params['city'])
      self.assertEqual(self.pm.state, params['state'])
      self.assertEqual(self.pm.zip, params['zip'])
      self.assertEqual(self.pm.last_four_digits, params['card_number'][-4:])
      self.assertEqual(self.pm.expiry_month, int(params['expiry_month']))
      self.assertEqual(self.pm.expiry_year, int(params['expiry_year']))

    def test_find_should_fail_on_an_invalid_token(self):
        pm = PaymentMethod.find('abc123')
        err = "Couldn't find PaymentMethod with token = abc123"
        self.assertIn({'context': 'system.general', 'key': 'default', 'subclass':'error', 'text':err}, pm.error_messages)

    def test_retain(self):
        pm = self.pm.retain()
        self.assertTrue(pm.is_retained)

    def test_redact(self):
        pm = self.pm.redact()
        self.assertTrue(pm.is_redacted)

if __name__ == '__main__':
    unittest.main()
