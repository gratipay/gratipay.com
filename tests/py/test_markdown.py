from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing import Harness
from gratipay.utils import markdown


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
