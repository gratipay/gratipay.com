from gratipay.testing import Harness
from gratipay.utils import markdown

from HTMLParser import HTMLParser

class TestMarkdown(Harness):

    def test_marky_works(self):
        md = "**Hello World!**"
        actual = HTMLParser().unescape(markdown.marky(md)).strip()
        expected = '<p><strong>Hello World!</strong></p>'
        assert actual == expected

    def test_marky_handles_npm_package(self):
        md = "# Greetings, program!\nGreetings. Program."
        pkg = {'name': 'greetings-program', 'description': 'Greetings, program.'}
        actual = HTMLParser().unescape(markdown.marky(md, pkg)).strip()
        expected = '''\
<h1 id="user-content-greetings-program" class="deep-link package-name-redundant package-description-redundant"><a href="#greetings-program">Greetings, program!</a></h1>
<p class="package-description-redundant">Greetings. Program.</p>'''
        assert actual == expected
