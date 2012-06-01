import sys
# Fix import path.
from os.path import abspath, dirname
cur_dir = dirname(abspath(__file__))
modules_dir = abspath('%s/..' % cur_dir)
sys.path.append(modules_dir)

import samurai.config as config
from samurai.payment_method import PaymentMethod

config.merchant_key = 'a1ebafb6da5238fb8a3ac9f6'
config.merchant_password = 'ae1aa640f6b735c4730fbb56'
config.processor_token = '5a0e1ca1e5a11a2997bbf912'
config.debug = True

def default_payment_method(options={}):
  data = {
      'sandbox' : True,
      'redirect_url' : 'http://test.host',
      'merchant_key' : config.merchant_key,
      'custom' : 'custom',
      'first_name' : 'FirstName',
      'last_name' : 'LastName',
      'address_1' : '1000 1st Av',
      'address_2' : '',
      'city' : 'Chicago',
      'state' : 'IL',
      'zip' : '10101',
      'card_number' : '4111111111111111',
      'cvv' : '111',
      'expiry_month' : '05',
      'expiry_year' : '2014',
    }

  data.update(options)
  return PaymentMethod.create(data.pop('card_number'),
                              data.pop('cvv'),
                              data.pop('expiry_month'),
                              data.pop('expiry_year'),
                              **data)
