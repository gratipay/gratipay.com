# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from gratipay.testing import Harness


FULL = """\

<p>Four score and seven years ago our fathers brought forth on this continent,
a new nation, conceived in Liberty, and dedicated to the proposition that all
men are created equal.</p>

<p>Now we are engaged in a great civil war, testing whether that nation, or any
nation so conceived and so dedicated, can long endure. We are met on a great
battle-field of that war. We have come to dedicate a portion of that field, as
a final resting place for those who here gave their lives that that nation
might live. It is altogether fitting and proper that we should do this.</p>

<p>But, in a larger sense, we can not dedicate&mdash;we can not
consecrate&mdash;we can not hallow&mdash;this ground. The brave men, living and
dead, who struggled here, have consecrated it, far above our poor power to add
or detract. The world will little note, nor long remember what we say here, but
it can never forget what they did here. It is for us the living, rather, to be
dedicated here to the unfinished work which they who fought here have thus far
so nobly advanced. It is rather for us to be here dedicated to the great task
remaining before us&mdash;that from these honored dead we take increased
devotion to that cause for which they gave the last full measure of
devotion&mdash;that we here highly resolve that these dead shall not have died
in vain&mdash;that this nation, under God, shall have a new birth of
freedom&mdash;and that government of the people, by the people, for the people,
shall not perish from the earth.</p>

"""


class TestSearch(Harness):

    def search(self, q):
        return self.client.GET("/search?q=" + q).body.decode('utf8')


    def test_includes_project(self):
        self.make_team(is_approved=True)
        assert 'Enterprise' in self.search('enterprise')

    def test_doesnt_display_project_description(self):
        self.make_team(is_approved=True, product_or_service="<i>Voyages!</i>")
        assert 'Voyages' not in self.search('enterprise')

    def test_includes_participant(self):
        self.make_participant('alice', claimed_time='now')
        assert 'alice' in self.search('alice')

    def test_displays_scrubbed_participant_statement_for_username_match(self):
        alice = self.make_participant('alice', claimed_time='now')
        alice.upsert_statement('en',
                           '<h1>Four</h1> score &amp; <script>seven&trade;</script> years ago ...')
        assert 'Four score &amp; seven\u2122 years ago \u2026' in self.search('alice')

    def test_displays_scrubbed_participant_statement_for_statement_match(self):
        alice = self.make_participant('alice', claimed_time='now')
        alice.upsert_statement('en',
                           '<h1>Four</h1> score &amp; <script>seven&trade;</script> years ago ...')
        assert '<b>Four</b> <b>score</b> &amp; seven\u2122 years' in self.search('four score')

    def test_truncates_statement_appropriately(self):
        alice = self.make_participant('alice', claimed_time='now')
        alice.upsert_statement('en', FULL)
        assert ('<span class="description">&middot; Four score and seven years ago our fathers '
                'brought forth on this continent, a new nation, conceived in Liberty, and '
                'dedicated to</span>') in self.search('alice')

    def test_excerpts_statement_appropriately(self):
        alice = self.make_participant('alice', claimed_time='now')
        alice.upsert_statement('en', FULL)
        assert ('&middot; &hellip; consecrate—we can not <b>hallow</b>—this ground. The brave '
                'men, living &hellip;') in self.search('hallow')

    def test_includes_unclaimed_packages_with_projects(self):
        self.make_package()
        body = self.search('fo')
        assert 'foo' in body
        assert 'has not joined' in body
        assert 'owned by'       not in body

    def test_does_not_include_claimed_packages(self):
        self.make_package(claimed_by='picard')
        body = self.search('fo')
        assert 'foo' in body
        assert 'has not joined' not in body
        assert 'owned by'       in body
