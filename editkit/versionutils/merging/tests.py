# coding=utf-8

from django.test import TestCase
from html import merge_html


class HTMLMergeTest(TestCase):
    def test_no_conflict(self):
        ancestor = '<p>First paragraph</p><p>Second paragraph</p>'
        mine = '<p>First paragraph</p><p>Second paragraph is awesome</p>'
        theirs = '<p>Second paragraph</p>'

        expected = '<p>Second paragraph is awesome</p>'
        self.assertEqual(merge_html(mine, theirs, ancestor), expected)

