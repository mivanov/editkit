import datetime

from django.test import TestCase
from django.conf import settings
from django.core.files.base import ContentFile
from django import db

from utils import TestSettingsManager
from models import *
from versionutils import diff
from versionutils.diff.diffutils import Registry, BaseFieldDiff, BaseModelDiff
from versionutils.diff.diffutils import TextFieldDiff
from versionutils.diff.diffutils import FileFieldDiff
from versionutils.diff.diffutils import ImageFieldDiff
from versionutils.diff.diffutils import HtmlFieldDiff


mgr = TestSettingsManager()
INSTALLED_APPS = list(settings.INSTALLED_APPS)
INSTALLED_APPS.append('versionutils.diff.tests')
mgr.set(INSTALLED_APPS=INSTALLED_APPS)


class ModelDiffTest(TestCase):
    def setUp(self):
        self.test_models = TEST_MODELS

    def tearDown(self):
        pass

    def test_identical(self):
        """
        The diff between two identical models, or a model and itself should be
        None.
        """
        vals = {'a': 'Lorem', 'b': 'Ipsum',
                'c': datetime.datetime.now(), 'd': 123}
        m1 = Diff_M1.objects.create(**vals)
        m2 = Diff_M1.objects.create(**vals)

        d = diff.diff(m1, m1).as_dict()
        self.assertEqual(d, None)

        d = diff.diff(m1, m2).as_dict()
        self.assertEqual(d, None)

    def test_nearly_identical(self):
        """
        The diff between models should consist of only the fields that are
        different.
        """
        vals = {'a': 'Lorem', 'b': 'Ipsum',
                'c': datetime.datetime.now(), 'd': 123}
        m1 = Diff_M1.objects.create(**vals)
        vals['a'] = 'Ipsum'
        m2 = Diff_M1.objects.create(**vals)
        d = diff.diff(m1, m2).as_dict()
        self.assertTrue(len(d) == 1)

    def test_foreign_key_identical(self):
        """
        The diff between two ForeignKey fields to the same object should be
        None.
        """
        vals = {'a': 'Lorem', 'b': 'Ipsum',
                'c': datetime.datetime.now(), 'd': 123}
        m1 = Diff_M1.objects.create(**vals)

        m3 = Diff_M4ForeignKey.objects.create(a=m1)
        m4 = Diff_M4ForeignKey.objects.create(a=m1)

        d = diff.diff(m3, m4).as_dict()
        self.assertTrue(d is None)

    def test_foreign_key(self):
        """
        The diff between two ForeignKey fields should be the same as the diff
        between the two objects referenced by the fields
        """
        vals = {'a': 'Lorem', 'b': 'Ipsum',
                'c': datetime.datetime.now(), 'd': 123}
        m1 = Diff_M1.objects.create(**vals)
        vals = {'a': 'Dolor', 'b': 'Ipsum',
                'c': datetime.datetime.now(), 'd': 123}
        m2 = Diff_M1.objects.create(**vals)

        m3 = Diff_M4ForeignKey.objects.create(a=m1)
        m4 = Diff_M4ForeignKey.objects.create(a=m2)

        d1 = diff.diff(m3, m4).as_dict()
        self.assertTrue(d1['a'])

        d2 = diff.diff(m1, m2).as_dict()

        self.assertEqual(d1['a'], d2)

    def test_historical_instance(self):
        o1 = Diff_M5Versioned(a="O1")
        o1.save()
        o2 = Diff_M5Versioned(a="O2")
        o2.save()


class FakeFieldDiffTest(TestCase):
    def test_property_diff(self):
        """
        The "fields" included in a diff don't have to be fields at all and can
        be properties, for example, as long as a custom ModelDiff is registered
        which dictates what FieldDiff to use for the "field".
        """
        diff.register(FakeFieldModel, FakeFieldModelDiff)
        a = FakeFieldModel(a='abc')
        b = FakeFieldModel(a='def')
        d = diff.diff(a, b)
        self.assertTrue(isinstance(d['b'], (TextFieldDiff,)))


class BaseFieldDiffTest(TestCase):
    def setUp(self):
        self.test_class = BaseFieldDiff

    def test_identical_fields_dict(self):
        """
        The diff between two identical fields of any type should be None.
        """
        vals = ['Lorem', 123, True, datetime.datetime.now()]
        for v in vals:
            d = self.test_class(v, v)
            self.assertEqual(d.as_dict(), None)

    def test_identical_fields_html(self):
        """
        The html of the diff between two identical fields should be a
        sensible message.
        """
        a = 'Lorem'
        d = self.test_class(a, a).as_html()
        self.assertTrue("No differences" in d)

    def test_deleted_inserted(self):
        a = 123
        b = 456
        d = self.test_class(a, b).as_dict()
        self.assertTrue(d['deleted'] == a)
        self.assertTrue(d['inserted'] == b)


class TextFieldDiffTest(BaseFieldDiffTest):
    def setUp(self):
        self.test_class = TextFieldDiff

    def test_deleted_inserted(self):
        a = 'abc'
        b = 'def'
        d = self.test_class(a, b).as_dict()
        self.assertTrue(len(d) == 2)
        self.assertTrue(d[0]['deleted'] == a)
        self.assertTrue(d[1]['inserted'] == b)

    def test_equal(self):
        a = 'abcdef'
        b = 'abcghi'
        d = self.test_class(a, b).as_dict()
        self.assertTrue(len(d) == 3)
        self.assertTrue(d[0]['equal'] == 'abc')


class FileFieldDiffTest(BaseFieldDiffTest):
    def setUp(self):
        self.test_class = FileFieldDiff

    def test_deleted_inserted(self):
        m1 = Diff_M2()
        m1.a.save("a.txt", ContentFile("TEST FILE"), save=False)

        m2 = Diff_M2()
        m2.a.save("b.txt", ContentFile("TEST FILE"), save=False)

        d = self.test_class(m1.a, m2.a).as_dict()
        self.assertTrue(d['deleted'].name == m1.a.name)
        self.assertTrue(d['inserted'].name == m2.a.name)

        m1.a.delete()
        m2.a.delete()


class ImageFieldDiffTest(FileFieldDiffTest):
    def setUp(self):
        self.test_class = ImageFieldDiff


class HtmlFieldTest(TestCase):
    def test_identical_fields(self):
        htmlDiff = HtmlFieldDiff('abc', 'abc')
        self.assertEquals(htmlDiff.as_dict(), None)

    def test_deleted_inserted(self):
        htmlDiff = HtmlFieldDiff('abc', 'def')
        self.assertTrue('def</ins>' in htmlDiff.as_html())


class DiffRegistryTest(TestCase):
    def setUp(self):
        self.registry = Registry()

        vals = {'a': 'Lorem', 'b': 'Ipsum',
                'c': datetime.datetime.now(), 'd': 123}
        m1 = Diff_M1.objects.create(**vals)

    def test_can_handle_any_field(self):
        """
        Out of the box, the registry should offer diff utils for any field.
        """
        r = self.registry
        field_types = [db.models.CharField, db.models.TextField,
                       db.models.BooleanField]
        for t in field_types:
            d = r.get_diff_util(t)
            self.assertTrue(issubclass(d, BaseFieldDiff))

    def test_can_handle_any_model(self):
        """
        Out of the box, the registry should offer diff utils for any model.
        """
        r = self.registry
        for t in TEST_MODELS:
            d = r.get_diff_util(t)
            self.assertTrue(issubclass(d, BaseModelDiff))

    def test_fallback_diff(self):
        class AwesomeImageField(db.models.ImageField):
            pass
        """
        If we don't have a diff util for the exact field type, we should fall
        back to the diff util for the base class, until we find a registered
        util.
        """
        self.registry.register(db.models.FileField, FileFieldDiff)
        d = self.registry.get_diff_util(AwesomeImageField)
        self.assertTrue(issubclass(d, FileFieldDiff))

    def test_register_model(self):
        """
        If we register a diff for a model, we should get that and not
        BaseModelDiff.
        """
        self.registry.register(Diff_M1, Diff_M1Diff)
        self.failUnlessEqual(self.registry.get_diff_util(Diff_M1), Diff_M1Diff)

    def test_register_field(self):
        """
        If we register a fielddiff for a model, we should get that and not
        BaseFieldDiff.
        """
        self.registry.register(db.models.CharField, Diff_M1FieldDiff)
        self.failUnlessEqual(self.registry.get_diff_util(db.models.CharField),
                             Diff_M1FieldDiff)

    def test_cannot_diff_something_random(self):
        """
        If we try to diff something that is neither a model nor a field,
        raise exception.
        """
        self.failUnlessRaises(diff.diffutils.DiffUtilNotFound,
                              self.registry.get_diff_util, DiffRegistryTest)
