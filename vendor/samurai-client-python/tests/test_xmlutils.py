import unittest
import datetime
import test_helper
from samurai.xmlutils import xml_to_dict, dict_to_xml

class TestXmlutils(unittest.TestCase):
    def test_xml_to_dict(self):
        test = '''
        <payment_method>
        <payment_method_token>QhLaMNNpvHwfnFbHbUYhNxadx4C</payment_method_token>
        <created_at type="datetime">2011-02-12T20:20:46Z</created_at>
        <updated_at type="datetime">2011-04-22T17:57:30Z</updated_at>
        <custom>Any value you want us to save with this payment method.</custom>
        <is_retained type="boolean">true</is_retained>
        <is_redacted type="boolean">false</is_redacted>
        <is_sensitive_data_valid type="boolean">false</is_sensitive_data_valid>
        <messages>
            <message class="error" context="input.cvv" key="too_long" />
            <message class="error" context="input.card_number" key="failed_checksum" />
            <message class="error" context="system.general" key="fubar">Error description</message>
        </messages>
        <last_four_digits>1111</last_four_digits>
        <card_type>visa</card_type>
        <first_name>Bob</first_name>
        <last_name>Smith</last_name>
        <expiry_month type="integer">1</expiry_month>
        <expiry_year type="integer">2020</expiry_year>
        <address_1 nil="true"></address_1>
        <address_2 nil="true"></address_2>
        <city nil="true"></city>
        <state nil="true"></state>
        <zip nil="true"></zip>
        <country nil="true"></country>
        </payment_method>
        '''

        expected = {'payment_method': {'address_1': {'nil': 'true'},
        'address_2': {'nil': 'true'},
        'card_type': 'visa',
        'city': {'nil': 'true'},
        'country': {'nil': 'true'},
        'created_at': datetime.datetime(2011, 2, 12, 20, 20, 46),
        'custom': 'Any value you want us to save with this payment method.',
        'expiry_month': 1,
        'expiry_year': 2020,
        'first_name': 'Bob',
        'is_redacted': False,
        'is_retained': True,
        'is_sensitive_data_valid': False,
        'last_four_digits': '1111',
        'last_name': 'Smith',
        'messages': {
            'message': [
                {'class': 'error', 'context': 'input.cvv', 'key': 'too_long'},
                {'class': 'error', 'context': 'input.card_number', 'key': 'failed_checksum'},
                {'class': 'error', 'context': 'system.general', 'key': 'fubar', 'text': 'Error description'}
            ]
        },
        'payment_method_token': 'QhLaMNNpvHwfnFbHbUYhNxadx4C',
        'state': {'nil': 'true'},
        'updated_at': datetime.datetime(2011, 4, 22, 17, 57, 30),
        'zip': {'nil': 'true'}}}

        self.assertEqual(expected, xml_to_dict(test))

    def test_dict_to_xml(self):
        dict_xml = {'transaction': {'amount': '100.00', 'currency_code': 'USD', 'something':True}}
        expected = '<transaction><amount>100.00</amount><something>true</something><currency_code>USD</currency_code></transaction>'
        self.assertEqual(expected, dict_to_xml(dict_xml))

if __name__ == '__main__':
    unittest.main()
