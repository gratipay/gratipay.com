# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing import Harness
from gratipay.utils import markdown


class TestRender(Harness):

    def test_renders(self):
        expected = "<p>Example</p>\n"
        actual = markdown.render('Example')
        assert expected == actual

    def test_escapes_scripts(self):
        expected = '<p>Example alert &ldquo;hi&rdquo;;</p>\n'
        actual = markdown.render('Example <script>alert "hi";</script>')
        assert expected == actual

    def test_renders_http_links(self):
        expected = '<p><a href="http://example.com/">foo</a></p>\n'
        assert markdown.render('[foo](http://example.com/)') == expected
        expected = '<p><a href="http://example.com/">http://example.com/</a></p>\n'
        assert markdown.render('<http://example.com/>') == expected

    def test_renders_https_links(self):
        expected = '<p><a href="https://example.com/">foo</a></p>\n'
        assert markdown.render('[foo](https://example.com/)') == expected
        expected = '<p><a href="https://example.com/">https://example.com/</a></p>\n'
        assert markdown.render('<https://example.com/>') == expected

    def test_escapes_javascript_links(self):
        expected = '<p>[foo](javascript:foo)</p>\n'
        assert markdown.render('[foo](javascript:foo)') == expected
        expected = '<p>&lt;javascript:foo&gt;</p>\n'
        assert markdown.render('<javascript:foo>') == expected

    def test_doesnt_allow_any_explicit_anchors(self):
        expected = '<p>foo</p>\n'
        assert markdown.render('<a href="http://example.com/">foo</a>') == expected
        expected = '<p>foo</p>\n'
        assert markdown.render('<a href="https://example.com/">foo</a>') == expected
        expected = '<p>foo</p>\n'
        assert markdown.render('<a href="javascript:foo">foo</a>') == expected

    def test_autolinks(self):
        expected = '<p><a href="http://google.com/">http://google.com/</a></p>\n'
        actual = markdown.render('http://google.com/')
        assert expected == actual

    def test_no_intra_emphasis(self):
        expected = '<p>Examples like this_one and this other_one.</p>\n'
        actual = markdown.render('Examples like this_one and this other_one.')
        assert expected == actual

    def test_returns_a_Markup(self):
        assert type(markdown.render('&')) is markdown.Markup


class TestRenderAndScrub(Harness):

    def test_renders_and_scrubs_markdown(self):
        assert markdown.render_and_scrub('**Greetings, program!**') == 'Greetings, program!'

    def test_is_fine_with_an_empty_string(self):
        assert markdown.render_and_scrub('') == ''

    def test_scrubs_direct_html(self):
        assert markdown.render_and_scrub('<b>Greetings, program!</b>') == 'Greetings, program!'

    def test_scrubs_tricky_scripts(self):
        # http://stackoverflow.com/q/753052#comment24080274_4869782
        assert markdown.render_and_scrub('<script<script>>alert("Hi!")<</script>/script>') == \
                                                        '&gt;alert(\u201cHi!\u201d)&lt;/script&gt;'

    def test_scrubs_comments(self):
        # http://stackoverflow.com/a/19730306
        assert markdown.render_and_scrub('<img<!-- --> src=x onerror=alert(1);//><!-- -->') == \
                                              'src=x onerror=alert(1);//&gt;&lt;!\u2013 \u2013&gt;'

    def test_renders_entity_references(self):
        assert markdown.render_and_scrub('&trade;') == '\u2122'

    def test_scrubs_rtlo(self):
        assert markdown.render_and_scrub('ed.io/about&#8238;3p\u202Em.exe') == 'ed.io/about3pm.exe'

    def test_render_does_not_render_entity_references_it_really_is_striptags(self):
        assert markdown.render('&trade;') == '<p>&trade;</p>\n'
        assert markdown.render_and_scrub('&trade;') == '\u2122'

    def test_does_not_double_escape(self):
        assert markdown.render_and_scrub('&amp;') == '&amp;'

    def test_returns_a_Markup(self):
        assert type(markdown.render_and_scrub('<p>&amp;</p>')) is markdown.Markup

    def test_escapes_single_quotes_but_still_doesnt_double_escape(self):
        assert markdown.render_and_scrub("&lt;a href='javascript:'&gt;Click Here&lt;/a&gt;") ==\
                                         '&lt;a href=&#39;javascript:&#39;&gt;Click Here&lt;/a&gt;'

    def test_catches_unicode_code_points(self):
        assert markdown.render_and_scrub('\u0022') == '\u201c'  # " → “
        assert markdown.render_and_scrub('\u0026') == '&amp;'   # &
        assert markdown.render_and_scrub('\u0027') == '&#39;'   # '
        assert markdown.render_and_scrub('\u003c') == '&lt;'    # <
        assert markdown.render_and_scrub('\u003e') == ''        # > is stripped, I guess?
