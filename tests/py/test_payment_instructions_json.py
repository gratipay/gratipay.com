import json

from gratipay.testing import Harness

class TestPaymentInstructionApi(Harness):

    def test_get_with_team_filter(self):
        "Test that GET with team_slug passed returns correct response."

        alice = self.make_participant("alice", claimed_time='now')
        Enterprise = self.make_team("The Enterprise", is_approved=True)
        Trident = self.make_team("The Trident", is_approved=True)

        alice.set_payment_instruction(Enterprise, '10.0')
        alice.set_payment_instruction(Trident, '12.0')

        data = json.loads(self.client.GET(
             "~/alice/payment-instructions.json?team_slug=" + Enterprise.slug
            , auth_as='alice').body)

        assert data['team_slug'] == Enterprise.slug
        assert data['team_name'] == Enterprise.name
        assert data['amount'] == '10.00'
        assert 'ctime' in data
        assert 'mtime' in data
        assert 'due' in data

    def test_get_with_team_filter_raises_error_on_invalid_team_slug(self):
        self.make_participant("alice", claimed_time = 'now')

        response = self.client.GxT(
             "~/alice/payment-instructions.json?team_slug=no-team"
            , auth_as='alice')

        assert response.code == 400

    # pi => payment instruction.

    def test_get_with_team_filter_returns_default_if_no_pi(self):
        self.make_participant("alice", claimed_time='now')
        Enterprise = self.make_team("The Enterprise", is_approved=True)

        data = json.loads(self.client.GET(
             "~/alice/payment-instructions.json?team_slug=" + Enterprise.slug
            , auth_as='alice').body)

        assert data['team_slug'] == Enterprise.slug
        assert data['team_name'] == Enterprise.name
        assert data['amount'] == '0.00'
        assert data['due'] == '0.00'
        assert data['ctime'] == None
        assert data['mtime'] == None

    def test_simple_get(self):
        "Test that GET without any parameters returns correct response."

        alice = self.make_participant("alice", claimed_time='now')
        Enterprise = self.make_team("The Enterprise", is_approved=True)
        Trident = self.make_team("The Trident", is_approved=True)

        data = json.loads(self.client.GET(
             "~/alice/payment-instructions.json", auth_as='alice').body)

        assert len(data) == 0 # Empty 'array' should be returned.

        alice.set_payment_instruction(Enterprise, '10.0')
        alice.set_payment_instruction(Trident, '12.0')

        data = json.loads(self.client.GET(
             "~/alice/payment-instructions.json", auth_as='alice').body)

        assert len(data) == 2

        assert data[0]['team_slug'] == Trident.slug # response is ordered by amount desc
        assert data[0]['amount'] == '12.00'
        assert data[0]['team_name'] == Trident.name

        assert data[1]['team_slug'] == Enterprise.slug
        assert data[1]['amount'] == '10.00'
        assert data[1]['team_name'] == Enterprise.name

        for d in data:
            assert 'due' in d
            assert 'ctime' in d
            assert 'mtime' in d
 
    def test_post(self):
        "Test that POST to this endpoint works correctly."

        self.make_participant("alice", claimed_time='now')
        Enterprise = self.make_team("The Enterprise", is_approved=True)
        Trident = self.make_team("The Trident", is_approved=True)

        request_body = [
            { 'amount': "1.50", 'team_slug': Enterprise.slug },
            { 'amount': "39.50", 'team_slug': Trident.slug }
        ]

        response = self.client.POST( "~/alice/payment-instructions.json"
                                    , body=json.dumps(request_body)
                                    , content_type='application/json'
                                    , auth_as='alice')

        assert response.code == 200

        # Make sure apt response returned.
        data = json.loads(response.body)

        assert len(data) == 2

        assert data[0]['team_slug'] == Enterprise.slug
        assert data[0]['team_name'] == Enterprise.name
        assert data[0]['amount'] == '1.50'

        assert data[1]['team_slug'] == Trident.slug
        assert data[1]['team_name'] == Trident.name
        assert data[1]['amount'] == '39.50'

        for d in data:
            assert 'due' in d
            assert 'ctime' in d
            assert 'mtime' in d

        # Make sure actually written to database.
        data = json.loads(self.client.GET(
             "~/alice/payment-instructions.json", auth_as='alice').body)

        assert data[0]['team_slug'] == Trident.slug
        assert data[0]['amount'] == '39.50'

        assert data[1]['team_slug'] == Enterprise.slug
        assert data[1]['amount'] == '1.50'

    def test_post_with_no_team_slug_key_returns_error(self):
        self.make_participant("alice", claimed_time='now')

        response = self.client.POST( "~/alice/payment-instructions.json"
                                    , body=json.dumps([{ 'amount': "1.50" }])
                                    , content_type='application/json'
                                    , auth_as='alice')

        assert response.code == 200 # Since batch processing.
        assert 'error' in json.loads(response.body)[0]

        data = json.loads(self.client.GET(
             "~/alice/payment-instructions.json", auth_as='alice').body)
        assert len(data) == 0

    def test_post_with_no_amount_key_returns_error(self):
        self.make_participant("alice", claimed_time='now')
        Enterprise = self.make_team("The Enterprise", is_approved=True)

        response = self.client.POST( "~/alice/payment-instructions.json"
                                    , body=json.dumps(
                                        [{ 'team_slug': Enterprise.slug }])
                                    , content_type='application/json'
                                    , auth_as='alice')

        assert response.code == 200
        assert 'error' in json.loads(response.body)[0]

        data = json.loads(self.client.GET(
             "~/alice/payment-instructions.json", auth_as='alice').body)
        assert len(data) == 0

    def test_adding_pi_for_invalid_team_returns_error(self):
        self.make_participant("alice", claimed_time='now')

        request_body = [{ 'team_slug': 'no-slug', 'amount': '39.50' }]

        response = self.client.POST( "~/alice/payment-instructions.json"
                                    , body=json.dumps(request_body)
                                    , content_type='application/json'
                                    , auth_as='alice')

        assert response.code == 200
        assert 'error' in json.loads(response.body)[0]

        data = json.loads(self.client.GET(
             "~/alice/payment-instructions.json", auth_as='alice').body)
        assert len(data) == 0

    def test_adding_pi_for_unapproved_team_returns_error(self):
        self.make_participant("alice", claimed_time='now')
        Enterprise = self.make_team("The Enterprise", is_approved=False)

        request_body = [{ 'team_slug': Enterprise.slug, 'amount': '39.50' }]

        response = self.client.POST( "~/alice/payment-instructions.json"
                                    , body=json.dumps(request_body)
                                    , content_type='application/json'
                                    , auth_as='alice')

        assert response.code == 200
        assert 'error' in json.loads(response.body)[0]

        data = json.loads(self.client.GET(
             "~/alice/payment-instructions.json", auth_as='alice').body)
        assert len(data) == 0
