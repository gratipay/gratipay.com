# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import json

from aspen.testing.client import FileUpload
from gratipay.testing import Harness, IMAGE, T


class TestTeamEdit(Harness):

    def test_edit(self):
        self.make_team(slug='enterprise', is_approved=True)
        edit_data = {
            'name': 'Enterprise',
            'product_or_service': 'We save galaxies.',
            'homepage': 'http://starwars-enterprise.com/',
            'image': FileUpload(IMAGE, 'logo.png'),
        }
        data = json.loads(self.client.POST( '/enterprise/edit/edit.json'
                                          , data=edit_data
                                          , auth_as='picard'
                                           ).body)

        team = T('enterprise')
        assert data == team.to_dict()

        assert team.name == 'Enterprise'
        assert team.product_or_service == 'We save galaxies.'
        assert team.homepage == 'http://starwars-enterprise.com/'
        assert team.load_image('original') == IMAGE

    def test_edit_supports_partial_updates(self):
        self.make_team(slug='enterprise', is_approved=True)
        edit_data = {
            'product_or_service': 'We save galaxies.',
            'homepage': 'http://starwars-enterprise.com/',
            'image': FileUpload(IMAGE, 'logo.png'),
        }
        self.client.POST( '/enterprise/edit/edit.json'
                        , data=edit_data
                        , auth_as='picard'
                         )

        team = T('enterprise')
        assert team.name == 'The Enterprise'
        assert team.product_or_service == 'We save galaxies.'
        assert team.homepage == 'http://starwars-enterprise.com/'
        assert team.load_image('original') == IMAGE

    def test_edit_needs_auth(self):
        self.make_team(slug='enterprise', is_approved=True)
        response = self.client.PxST( '/enterprise/edit/edit.json'
                                   , data={'name': 'Enterprise'}
                                    )
        assert response.code == 401
        assert T('enterprise').name == 'The Enterprise'

    def test_only_admin_and_owner_can_edit(self):
        self.make_participant('alice', claimed_time='now')
        self.make_participant('admin', claimed_time='now', is_admin=True)
        self.make_team(slug='enterprise', is_approved=True)

        response = self.client.PxST( '/enterprise/edit/edit.json'
                                   , data={'name': 'Enterprise'}
                                   , auth_as='alice'
                                    )
        assert response.code == 403
        assert T('enterprise').name == 'The Enterprise'

        response = self.client.POST( '/enterprise/edit/edit.json'
                                   , data={'name': 'Enterprise'}
                                   , auth_as='admin'
                                    )
        assert response.code == 200
        assert T('enterprise').name == 'Enterprise'

        # test_edit() passes => owner can edit

    def test_cant_edit_closed_teams(self):
        self.make_team(slug='enterprise', is_approved=True)
        self.db.run("UPDATE teams SET is_closed = true WHERE slug = 'enterprise'")

        response = self.client.PxST( '/enterprise/edit/edit.json'
                                    , data={'name': 'Enterprise'}
                                    , auth_as='picard'
                                     )
        assert response.code in (403, 410)
        assert T('enterprise').name == 'The Enterprise'

    def test_cant_edit_rejected_teams(self):
        self.make_team(slug='enterprise', is_approved=False)
        response = self.client.PxST( '/enterprise/edit/edit.json'
                                    , data={'name': 'Enterprise'}
                                    , auth_as='picard'
                                     )
        assert response.code == 403
        assert T('enterprise').name == 'The Enterprise'

    def test_can_edit_teams_under_review(self):
        self.make_team(slug='enterprise', is_approved=None)
        response = self.client.POST( '/enterprise/edit/edit.json'
                                    , data={'name': 'Enterprise'}
                                    , auth_as='picard'
                                     )
        assert response.code == 200
        assert T('enterprise').name == 'Enterprise'

    def test_can_only_edit_allowed_fields(self):
        allowed_fields = set(['name', 'image', 'product_or_service', 'homepage'])

        team = self.make_team(slug='enterprise', is_approved=None)

        fields = vars(team).keys()
        fields.remove('onboarding_url')  # we are still keeping this in the db for now
        for field in fields:
            if field not in allowed_fields:
                response = self.client.POST( '/enterprise/edit/edit.json'
                                           , data={field: 'foo'}
                                           , auth_as='picard'
                                            )
                new_team = T('enterprise')
                assert response.code == 200
                assert getattr(new_team, field) == getattr(team, field)

    def test_edit_accepts_jpeg_and_png(self):
        team = self.make_team(slug='enterprise', is_approved=True)
        image_types = ['png', 'jpg', 'jpeg']
        for i_type in image_types:
            team.save_image(original='', large='', small='', image_type='image/png')
            data = {'image': FileUpload(IMAGE, 'logo.'+i_type)}
            response = self.client.POST( '/enterprise/edit/edit.json'
                                       , data=data
                                       , auth_as='picard'
                                        )
            assert response.code == 200
            assert team.load_image('original') == IMAGE

    def test_edit_with_invalid_image_type_raises_error(self):
        team = self.make_team(slug='enterprise', is_approved=True)
        invalid_image_types = ['tiff', 'gif', 'bmp', 'svg']
        for i_type in invalid_image_types:
            data = {'image': FileUpload(IMAGE, 'logo.'+i_type)}
            response = self.client.PxST( '/enterprise/edit/edit.json'
                                       , data=data
                                       , auth_as='picard'
                                        )
            assert response.code == 400
            assert "Please upload a PNG or JPG image." in response.body
            assert team.load_image('original') == None

    def test_edit_with_empty_values_raises_error(self):
        self.make_team(slug='enterprise', is_approved=True)
        response = self.client.PxST( '/enterprise/edit/edit.json'
                                   , data={'name': '   '}
                                   , auth_as='picard'
                                    )
        assert response.code == 400
        assert T('enterprise').name == 'The Enterprise'

    def test_edit_with_bad_url_raises_error(self):
        self.make_team( slug='enterprise'
                      , is_approved=True
                      , homepage='http://starwars-enterprise.com/')

        r = self.client.PxST( '/enterprise/edit/edit.json'
                            , data={'homepage': 'foo'}
                            , auth_as='picard'
                             )
        assert r.code == 400
        assert "Please enter an http[s]:// URL for the 'Homepage' field." in r.body
        assert T('enterprise').homepage == 'http://starwars-enterprise.com/'

    def test_edit_with_empty_data_does_nothing(self):
        team_data = {
            'slug': 'enterprise',
            'is_approved': True,
            'name': 'Enterprise',
            'product_or_service': 'We save galaxies.',
            'homepage': 'http://starwars-enterprise.com/',
        }
        self.make_team(**team_data)
        r = self.client.POST( '/enterprise/edit/edit.json'
                            , data={}
                            , auth_as='picard'
                             )
        assert r.code == 200

        team = T('enterprise')
        for field in team_data:
            assert getattr(team, field) == team_data[field]
