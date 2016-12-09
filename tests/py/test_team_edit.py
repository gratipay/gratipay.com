import base64
import json

from aspen.testing.client import FileUpload
from gratipay.testing import Harness, T


IMAGE = base64.b64decode(b"""\
/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0a
HBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIy
MjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAD9AeYDASIA
AhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQA
AAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3
ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWm
p6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEA
AwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSEx
BhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElK
U1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3
uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD5/pcH
GccUu47NvGM5puaAHvG6BWdGUONykjGR6imVP+8mgy82REAqqzc454ApkTrHIrMgcA5KknB9uKAI
6X61NPNHNdvKsCxxs5YRKThRnoO9NnaJ5maGMxxk/Khbdj8e9AEVLtO3dg49cU+GMSyqjSLGCfvP
0FStcTRW7WazlrcSFtqn5Semf0oArUVJKYSE8oODtG7cc898e1R0AFFFOVipJGORjkUANopSQcdB
UtwkMbgQTGVcAliu3n0oAhHHSlJJOScmkooAKKKKACiiigB6Ru+7aCdoyfYUypY7iWKORI3KrINr
gdxTBg5LHntx1oAbToygkBkUsmeQDg1Lc3AuZd4hii4A2xLgfWoKAFYqWO0EDPANJUrw7bdJfMjO
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
2Q==""")

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
