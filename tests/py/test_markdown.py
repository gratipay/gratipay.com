from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing import Harness, skipif_missing_marky_markdown
from gratipay.utils import markdown

from HTMLParser import HTMLParser


class TestMarkdown(Harness):

    # render

    def test_render_renders(self):
        expected = "<p>Example</p>\n"
        actual = markdown.render('Example')
        assert expected == actual

    def test_render_escapes_scripts(self):
        expected = '<p>Example alert &ldquo;hi&rdquo;;</p>\n'
        actual = markdown.render('Example <script>alert "hi";</script>')
        assert expected == actual

    def test_render_renders_http_links(self):
        expected = '<p><a href="http://example.com/">foo</a></p>\n'
        assert markdown.render('[foo](http://example.com/)') == expected
        expected = '<p><a href="http://example.com/">http://example.com/</a></p>\n'
        assert markdown.render('<http://example.com/>') == expected

    def test_render_renders_https_links(self):
        expected = '<p><a href="https://example.com/">foo</a></p>\n'
        assert markdown.render('[foo](https://example.com/)') == expected
        expected = '<p><a href="https://example.com/">https://example.com/</a></p>\n'
        assert markdown.render('<https://example.com/>') == expected

    def test_render_escapes_javascript_links(self):
        expected = '<p>[foo](javascript:foo)</p>\n'
        assert markdown.render('[foo](javascript:foo)') == expected
        expected = '<p>&lt;javascript:foo&gt;</p>\n'
        assert markdown.render('<javascript:foo>') == expected

    def test_render_doesnt_allow_any_explicit_anchors(self):
        expected = '<p>foo</p>\n'
        assert markdown.render('<a href="http://example.com/">foo</a>') == expected
        expected = '<p>foo</p>\n'
        assert markdown.render('<a href="https://example.com/">foo</a>') == expected
        expected = '<p>foo</p>\n'
        assert markdown.render('<a href="javascript:foo">foo</a>') == expected

    def test_render_autolinks(self):
        expected = '<p><a href="http://google.com/">http://google.com/</a></p>\n'
        actual = markdown.render('http://google.com/')
        assert expected == actual

    def test_render_no_intra_emphasis(self):
        expected = '<p>Examples like this_one and this other_one.</p>\n'
        actual = markdown.render('Examples like this_one and this other_one.')
        assert expected == actual


    # rln - render_like_npm

    @skipif_missing_marky_markdown
    def test_rln_works(self):
        md = "**Hello World!**"
        actual = HTMLParser().unescape(markdown.render_like_npm(md)).strip()
        expected = '<p><strong>Hello World!</strong></p>'
        assert actual == expected

    @skipif_missing_marky_markdown
    def test_rln_handles_npm_package(self):
        md = "# Greetings, program!\nGreetings. Program."
        pkg = {'name': 'greetings-program', 'description': 'Greetings, program.'}
        actual = HTMLParser().unescape(markdown.render_like_npm(md, pkg)).strip()
        expected = '''\
<h1 class="package-name-redundant package-description-redundant"><a id="user-content-greetings-program" class="deep-link" href="#greetings-program"><svg aria-hidden="true" class="deep-link-icon" height="16" version="1.1" width="16"><path d="M4 9h1v1H4c-1.5 0-3-1.69-3-3.5S2.55 3 4 3h4c1.45 0 3 1.69 3 3.5 0 1.41-.91 2.72-2 3.25V8.59c.58-.45 1-1.27 1-2.09C10 5.22 8.98 4 8 4H4c-.98 0-2 1.22-2 2.5S3 9 4 9zm9-3h-1v1h1c1 0 2 1.22 2 2.5S13.98 12 13 12H9c-.98 0-2-1.22-2-2.5 0-.83.42-1.64 1-2.09V6.25c-1.09.53-2 1.84-2 3.25C6 11.31 7.55 13 9 13h4c1.45 0 3-1.69 3-3.5S14.5 6 13 6z"></path></svg></a>Greetings, program!</h1>
<p class="package-description-redundant">Greetings. Program.</p>'''
        assert actual == expected
