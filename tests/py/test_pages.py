from __future__ import print_function, unicode_literals

import re
import json

from aspen import Response

import braintree
import mock
import pytest
from braintree.test.nonces import Nonces
from gratipay.security.user import SESSION
from gratipay.testing import Harness
from gratipay.wireup import find_files


overescaping_re = re.compile(r'&amp;(#[0-9]{4}|[a-z]+);')


class TestPages(Harness):

    def browse(self, setup=None, **kw):
        alice = self.make_participant('alice', claimed_time='now')

        # for pricing page
        self.make_team('Gratipay')

        # for the receipt page
        result = braintree.PaymentMethod.create({
            "customer_id": alice.get_braintree_account().id,
            "payment_method_nonce": Nonces.Transactable
        })
        assert result.is_success
        address = result.payment_method.token
        exchange_id = self.make_exchange('braintree-cc', 19, 0, alice, address=address)

        # for npm page
        self.db.run("INSERT INTO packages (package_manager, name, description, emails) "
                    "VALUES ('npm', 'foo-package', 'A package', ARRAY[]::text[])")

        if setup:
            setup(alice)
        i = len(self.client.www_root)
        urls = []
        for spt in find_files(self.client.www_root, '*.spt'):
            url = spt[i:-4].replace('/%team/', '/alice/') \
                           .replace('/alice/%sub', '/alice/foo') \
                           .replace('/~/%username/', '/~alice/') \
                           .replace('/for/%slug/', '/for/wonderland/') \
                           .replace('/%platform/', '/github/') \
                           .replace('/%package/', '/foo-package/') \
                           .replace('/%user_name/', '/gratipay/') \
                           .replace('/%to', '/1') \
                           .replace('/%country', '/TT') \
                           .replace('/%exchange_id.int', '/%s' % exchange_id) \
                           .replace('/%redirect_to', '/giving') \
                           .replace('/%endpoint', '/public') \
                           .replace('/about/me/%sub', '/about/me')
            assert '/%' not in url
            if 'index' in url.split('/')[-1]:
                url = url.rsplit('/', 1)[0] + '/'
            urls.append(url)
        urls.extend("""
           /about/me
           /about/me/
           /about/me/history
        """.split())
        for url in urls:
            try:
                r = self.client.GET(url, **kw)
            except Response as r:
                if r.code == 404 or r.code >= 500:
                    raise
            assert r.code != 404
            assert r.code < 500
            assert not overescaping_re.search(r.body.decode('utf8'))

    def test_anon_can_browse(self):
        self.browse()

    def test_new_participant_can_browse(self):
        self.browse(auth_as='alice')

    def test_on_the_fence_can_browse(self):
        def setup(alice):
            alice.update_is_free_rider(None)
        self.browse(setup, auth_as='alice')

    @pytest.mark.xfail(reason="migrating to Teams; #3399")
    def test_username_is_in_button(self):
        self.make_participant('alice', claimed_time='now')
        self.make_participant('bob', claimed_time='now')
        body = self.client.GET('/~alice/', auth_as='bob').body
        assert '<span class="zero">Give to alice</span>' in body

    @pytest.mark.xfail(reason="migrating to Teams; #3399")
    def test_username_is_in_unauth_giving_cta(self):
        self.make_participant('alice', claimed_time='now')
        body = self.client.GET('/~alice/').body
        assert 'give to alice' in body

    def test_widget(self):
        self.make_participant('cheese', claimed_time='now')
        expected = "javascript: window.open"
        actual = self.client.GET('/~cheese/widget.html').body
        assert expected in actual

    def test_github_associate(self):
        assert self.client.GxT('/on/github/associate').code == 400

    def test_twitter_associate(self):
        assert self.client.GxT('/on/twitter/associate').code == 400

    def test_about(self):
        expected = "We provide voluntary"
        actual = self.client.GET('/about/').body
        assert expected in actual

    def test_about_stats(self):
        expected = "Gratipay processes"
        actual = self.client.GET('/about/stats').body
        assert expected in actual

    def test_about_charts(self):
        assert self.client.GxT('/about/charts.html').code == 302

    def test_about_payment_distribution_json(self):
        distribution = json.loads(self.client.GET('/about/payment-distribution.json').body)
        assert len(distribution) == 13
        assert distribution[0]['xText'] == '1000.00'

    def test_about_teams_redirect(self):
        assert self.client.GxT('/about/teams/').code == 302
        assert self.client.GxT('/about/features/teams/').code == 302

    def test_about_payments(self):
        assert "Payments" in self.client.GET('/about/features/payments').body.decode('utf8')

    def test_about_payroll(self):
        assert "Payroll" in self.client.GET('/about/features/payroll').body.decode('utf8')

    def test_404(self):
        response = self.client.GET('/about/four-oh-four.html', raise_immediately=False)
        assert "Not Found" in response.body
        assert "{%" not in response.body

    def test_for_contributors_redirects_to_inside_gratipay(self):
        loc = self.client.GxT('/for/contributors/').headers['Location']
        assert loc == 'http://inside.gratipay.com/'

    def test_mission_statement_also_redirects(self):
        assert self.client.GxT('/for/contributors/mission-statement.html').code == 302

    def test_anonymous_sign_out_redirects(self):
        response = self.client.PxST('/sign-out.html')
        assert response.code == 302
        assert response.headers['Location'] == '/'

    def test_sign_out_overwrites_session_cookie(self):
        self.make_participant('alice')
        response = self.client.PxST('/sign-out.html', auth_as='alice')
        assert response.code == 302
        assert response.headers.cookie[SESSION].value == ''

    def test_sign_out_doesnt_redirect_xhr(self):
        self.make_participant('alice')
        response = self.client.PxST('/sign-out.html', auth_as='alice',
                                    HTTP_X_REQUESTED_WITH=b'XMLHttpRequest')
        assert response.code == 200

    def test_settings_page_available_balance(self):
        self.make_participant('alice', claimed_time='now')
        self.db.run("UPDATE participants SET balance = 123.00 WHERE username = 'alice'")
        actual = self.client.GET("/~alice/settings/", auth_as="alice").body
        expected = "123"
        assert expected in actual

    def test_giving_page(self):
        Enterprise = self.make_team(is_approved=True)
        alice = self.make_participant('alice', claimed_time='now')
        alice.set_payment_instruction(Enterprise, "1.00")
        assert "The Enterprise" in self.client.GET("/~alice/giving/", auth_as="alice").body

    def test_giving_page_shows_cancelled(self):
        Enterprise = self.make_team(is_approved=True)
        alice = self.make_participant('alice', claimed_time='now')
        alice.set_payment_instruction(Enterprise, "1.00")
        alice.set_payment_instruction(Enterprise, "0.00")
        assert "Cancelled" in self.client.GET("/~alice/giving/", auth_as="alice").body

    def test_new_participant_can_edit_profile(self):
        self.make_participant('alice', claimed_time='now')
        body = self.client.GET("/~alice/", auth_as="alice").body
        assert b'Edit' in body

    def test_tilde_slash_redirects_to_tilde(self):
        self.make_participant('alice', claimed_time='now')
        response = self.client.GxT("/~/alice/", auth_as="alice")
        assert response.code == 302
        assert response.headers['Location'] == '/~alice/'

    def test_tilde_slash_redirects_subpages_with_querystring_to_tilde(self):
        self.make_participant('alice', claimed_time='now')
        response = self.client.GxT("/~/alice/foo/bar?baz=buz", auth_as="alice")
        assert response.code == 302
        assert response.headers['Location'] == '/~alice/foo/bar?baz=buz'

    def test_username_redirected_to_tilde(self):
        self.make_participant('alice', claimed_time='now')
        response = self.client.GxT("/alice/", auth_as="alice")
        assert response.code == 302
        assert response.headers['Location'] == '/~alice/'

    def test_username_redirects_everything_to_tilde(self):
        self.make_participant('alice', claimed_time='now')
        response = self.client.GxT("/alice/foo/bar?baz=buz", auth_as="alice")
        assert response.code == 302
        assert response.headers['Location'] == '/~alice/foo/bar?baz=buz'

    def test_team_slug__not__redirected_from_tilde(self):
        self.make_team(is_approved=True)
        assert self.client.GET("/TheEnterprise/").code == 200
        assert self.client.GxT("/~TheEnterprise/").code == 404

    @mock.patch('gratipay.models.participant.Participant.get_braintree_account')
    @mock.patch('gratipay.models.participant.Participant.get_braintree_token')
    def test_braintree_linked_from_credit_card_page(self, foo, bar):
        self.make_participant('alice', claimed_time='now')
        body = self.client.GET("/~alice/routes/credit-card.html", auth_as="alice").body
        assert  "Braintree" in body

    def test_dashboard_is_403_for_anon(self):
        self.make_participant('admin', is_admin=True)
        assert self.client.GxT('/dashboard/').code == 403

    def test_dashboard_is_403_for_non_admin(self):
        self.make_participant('alice')
        assert self.client.GxT('/dashboard/', auth_as='alice').code == 403

    def test_dashboard_barely_works(self):
        self.make_participant('admin', is_admin=True)
        assert 'Unreviewed Accounts' in self.client.GET('/dashboard/', auth_as='admin').body

    def test_your_payment_template_basically_works(self):
        self.make_team(is_approved=True)
        self.make_participant('alice')
        assert 'your-payment' in self.client.GET('/TheEnterprise/', auth_as='alice').body
