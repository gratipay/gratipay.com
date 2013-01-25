from Cookie import SimpleCookie
from StringIO import StringIO

from aspen.http.request import Request
from aspen.testing import StubWSGIRequest
from aspen.testing.client import TestClient as AspenTestClient

from gittip.authentication import User
from gittip.testing import test_website


class TestClient(AspenTestClient):

    def add_cookie_info(self, request, cookie_info):
        if cookie_info:
            user = cookie_info.get('user')
            if user is not None:
                user = User.from_id(user)
                # Note that Cookie needs a bytestring.
                request.headers.cookie['session'] = user.session_token
