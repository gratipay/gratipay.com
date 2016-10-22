from gratipay.testing import Harness
from gratipay.utils import markdown

from HTMLParser import HTMLParser

class TestMarkdown(Harness):

    def test_marky_works(self):
        md = "**Hello World!**"
        actual = HTMLParser().unescape(markdown.marky(md)).strip()
        expected = '<p><strong>Hello World!</strong></p>'
        assert actual == expected
