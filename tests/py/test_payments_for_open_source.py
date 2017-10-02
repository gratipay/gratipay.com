# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.homepage import _charge
from gratipay.models.payment_for_open_source import PaymentForOpenSource
from gratipay.testing import Harness, IMAGE


class TestPaymentForOpenSource(Harness):

    def test_can_insert(self):
        self.make_payment_for_open_source()
        assert self.db.one('SELECT * FROM payments_for_open_source').name == 'Alice Liddell'

    def test_can_fetch(self):
        uuid = self.make_payment_for_open_source().uuid
        assert PaymentForOpenSource.from_uuid(uuid).name == 'Alice Liddell'

    def test_can_update(self):
        pfos = self.make_payment_for_open_source()
        assert pfos.braintree_transaction_id is None
        assert pfos.braintree_result_message is None
        assert not pfos.succeeded

        _charge(self.app, pfos, 'fake-valid-nonce')

        assert pfos.braintree_transaction_id is not None
        assert pfos.braintree_result_message == ''
        assert pfos.succeeded

        fresh = self.db.one("SELECT pfos.*::payments_for_open_source "
                            "FROM payments_for_open_source pfos")
        assert fresh.braintree_transaction_id is not None
        assert fresh.braintree_result_message == ''
        assert fresh.succeeded


    # Images
    # ======

    def test_save_image_saves_image(self):
        pfos = self.make_payment_for_open_source()
        pfos.save_image(IMAGE, IMAGE, IMAGE, 'image/png')
        media_type = self.db.one('SELECT image_type FROM payments_for_open_source '
                                 'WHERE id=%s', (pfos.id,))
        assert media_type == 'image/png'

    def test_save_image_records_the_event(self):
        pfos = self.make_payment_for_open_source()
        oids = pfos.save_image(IMAGE, IMAGE, IMAGE, 'image/png')
        event = self.db.all('SELECT * FROM events ORDER BY ts DESC')[0]
        assert event.type == 'payment_for_open_source'
        assert event.payload == { 'action': 'upsert_image'
                                , 'original': oids['original']
                                , 'large': oids['large']
                                , 'small': oids['small']
                                , 'id': pfos.id
                                 }

    def test_load_image_loads_image(self):
        pfos = self.make_payment_for_open_source()
        pfos.save_image(IMAGE, IMAGE, IMAGE, 'image/png')
        image = pfos.load_image('large')  # buffer
        assert str(image) == IMAGE

    def test_image_endpoint_serves_an_image(self):
        pfos = self.make_payment_for_open_source()
        pfos.save_image(IMAGE, IMAGE, IMAGE, 'image/png')
        image = self.client.GET('/browse/payments/{}/image'.format(pfos.uuid)).body  # buffer
        assert str(image) == IMAGE

    def test_get_image_url_gets_image_url(self):
        pfos = self.make_payment_for_open_source()
        pfos.save_image(IMAGE, IMAGE, IMAGE, 'image/png')
        expected = '/browse/payments/{}/image?size=small'.format(pfos.uuid)
        assert pfos.get_image_url('small') == expected
