import difflib
import re
import mimetypes

from django.db import models
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django import forms
from django.conf import settings
from django.contrib.gis.db import models as gis_models

from utils import static_url
import diff_match_patch
import daisydiff
from versionutils.versioning.utils import is_historical_instance


class DiffUtilNotFound(Exception):
    """
    No appropriate diff util registered for this object.
    """
    pass


class BaseFieldDiff(object):
    """
    Simplest diff possible, used when no better option is available.
    Just shows two fields side-by-side, in the case of HTML output.
    To customize how two fields get compared, subclass BaseFieldDiff,
    implement (at minimum) get_diff() and as_html() and register your
    class either for a certain field type or for a specific field of a
    specific model.  See BaseModelDiff for details on the latter.

    Here's how you might create your own diff util and register it for
    a field type::

        class MyIntegerDiff(BaseFieldDiff):
            def get_diff(self):
                if self.field1 == self.field2:
                    return None
                return {'difference': (self.field2 - self.field1)}

            def as_html(self):
                d = self.get_diff()
                if d is None:
                    return 'Values are the same'
                if d['difference'] > 0:
                    return 'New value is larger'
                return 'New value is smaller'

        diff.register(models.IntegerField, MyIntegerDiff)

    Attributes:
        field1: The first value you want to diff.
        field2: The second value you want to diff, against field1.
        template: An optional filename of the template to use when rendering.
    """
    __metaclass__ = forms.MediaDefiningClass
    template = None

    def __init__(self, field1, field2):
        """
        Args:
            field1: The first value you want to diff.
            field2: The second value you want to diff, against field1.
        """
        self.field1 = field1
        self.field2 = field2

    def get_diff(self):
        """
        Compares the two field values (field1 and field2).

        Returns:
            A dictionary containing the diff information.  This dictionary
            can then be used by as_html() for rendering HTML.  Returns None
            if the field values are equal.
        """
        if self.field1 == self.field2:
            return None
        return {'deleted': self.field1, 'inserted': self.field2}

    def as_dict(self):
        """
        Returns:
            The diff as a dictionary or array of dictionaries.
        """
        return self.get_diff()

    def as_html(self):
        """
        Returns:
            A string of the diff between field1 and field2.  These are normally
            one row of an HTML table, with two cells in a side-by-side diff.
        """
        diff = self.as_dict()
        if self.template:
            return render_to_string(self.template, diff)

        if diff is None:
            return '<tr><td colspan="2">(No differences found)</td></tr>'
        return '<tr><td>%s</td><td>%s</td></tr>' % (self.field1, self.field2)

    def _media(self):
        return forms.Media()
    media = property(_media)

    def __str__(self):
        return self.as_html()

    def __unicode__(self):
        return mark_safe(unicode(self.__str__()))


class BaseModelDiff(object):
    """
    Diff util used for comparing two model instances.  By default, it will
    compare the instances on all of their fields, except AutoFields.
    To customize which fields to compare, subclass BaseModelDiff, setting the
    'fields' or 'excludes' attributes like this::

        class MyModelDiff(diff.BaseModelDiff):
            fields =   ('name',
                        'contents')

    and then register it with your model like this::

        diff.register(MyModel, MyModelDiff)

    You can also customize how each field is compared by using a tuple
    ('field_name', FieldDiff) instead of just the field names, like this::

        class MyModelDiff(diff.BaseModelDiff):
            fields =   ( ('name', diff.TextFieldDiff),
                         ('contents', diff.HtmlFieldDiff),
                       )

    Attributes:
        fields: An optional tuple containing either field names or
            ('field_name', FieldDiff).  The listed fields will be
            diffed.
        excludes: An optional tuple of field names to ignore.

    """
    fields = None
    excludes = ()

    def __init__(self, model1, model2, model_class=None):
        """
        Args:
            model1: The first model instance you want to diff.
            model2: The second model instance you want to diff,
                against model1.
            model_class: Optional parameter that indicates the
                model class to consider when diffing.
        """
        self.model1 = model1
        self.model2 = model2
        if model_class:
            self.model_class = model_class
        else:
            self.model_class = self.model1.__class__
        self._diff = None

    def as_dict(self):
        """
        Returns:
            The diff as a dictionary or array of dictionaries.
        """
        diffs = {}
        for field, field_diff in self.get_diff().items():
            field_diff_dict = field_diff.as_dict()
            if field_diff_dict:
                diffs[field] = field_diff_dict
        if not diffs:
            diffs = None
        return diffs

    def as_html(self):
        """
        Renders the diffs between the model instances as an HTML table. Only
        those fields that are different will be rendered as rows in the
        table. Fields that are not different will be skipped.

        Returns:
            An html string string representing the differences between
            model1 and model2.
        """
        diffs = self.get_diff()
        diff_str = []
        if self.fields:
            display_order = self.fields
        else:
            display_order = diffs.keys()
        for name in display_order:
            if not isinstance(name, basestring):
                name = name[0]
            if diffs[name].get_diff():
                diff_str.append('<tr><td colspan="2">%s</td></tr>' % (name, ))
                diff_str.append('%s' % (diffs[name], ))
        if diff_str:
            return '\n'.join(diff_str)
        return '<tr><td colspan="2">No differences found</td></tr>'

    def get_diff(self):
        """
        Returns:
            A dictionary that contains all field diffs, indexed by field name.
        """
        if self._diff is not None:
            return self._diff
        diff = {}
        diff_utils = {}

        if self.fields:
            diff_fields = self.fields
        else:
            diff_fields = [f.name for f in self.model_class._meta.fields]

        for name in diff_fields:
            if isinstance(name, basestring):
                field = self.model_class._meta.get_field(name)
                if isinstance(field, (models.AutoField,)):
                    continue
                diff_utils[name] = registry.get_diff_util(field.__class__)
            else:
                diff_utils[name[0]] = name[1]

        for field_name, diff_class in diff_utils.items():
            if field_name in self.excludes:
                continue

            obj1 = getattr(self.model1, field_name)
            obj2 = getattr(self.model2, field_name)
            is_model_diff = issubclass(diff_class, BaseModelDiff)

            if is_model_diff:
                # Use the non-versioned class to do the diff on the
                # versioned fields.
                if is_historical_instance(obj1):
                    base_class = obj1.version_info._object.__class__
                else:
                    base_class = obj1.__class__
                diff[field_name] = diff_class(obj1, obj2,
                    model_class=base_class)
            else:
                diff[field_name] = diff_class(obj1, obj2)

        self._diff = diff
        return diff

    def __getitem__(self, name):
        "Returns a FieldDiff with the given name."
        d = self.get_diff()
        try:
            field = d[name]
        except KeyError:
            raise KeyError('Key %r not found in Model Diff' % name)
        return field

    def _media(self):
        # Add all the field diffs' media attributes together.
        # Because the field diffs don't compute anything until their
        # relevant get_diff() methods are called, this isn't expensive.
        m = forms.Media()
        for name, field_diff in self.get_diff().iteritems():
            m += field_diff.media
        return m
    media = property(_media)

    def __str__(self):
        return self.as_html()

    def __unicode__(self):
        """
        For use in templates, returns a safe string.
        """
        return mark_safe(unicode(self.__str__()))


class TextFieldDiff(BaseFieldDiff):
    """
    Compares the fields as text and renders the diff in an easy to read format.
    """
    template = 'diff/text_diff.html'

    def as_html(self):
        d = self.get_diff()
        if d is None:
            return '<tr><td colspan="2">(No differences found)</td></tr>'
        return render_to_string(self.template, {'diff': d})

    def get_diff(self):
        return get_diff_operations_clean(self.field1, self.field2)


class HtmlFieldDiff(BaseFieldDiff):
    """
    Compares the fields as HTML and renders them side-by-side, with the
    deleted, inserted, and changed text and elements highlighted.
    To use for a field type, first register in your code like this:
    diff.register(MyHtmlField, diff.HtmlFieldDiff)
    """
    def as_html(self):
        d = self.get_diff()
        if d is None:
            return '<tr><td colspan="2">(No differences found)</td></tr>'
        return ('<tr class="htmldiff"><td>%s</td><td>%s</td></tr>'
                                          % (d['deleted'], d['inserted']))

    def get_diff(self):
        if self.field1 == self.field2:
            return None
        return {'deleted': self.field1, 'inserted': self.field2}

    class Media:
        js = (static_url('js/diff_match_patch/diff_match_patch_uncompressed.js'),
              static_url('js/diff/htmldiff.js'),
              static_url('js/jquery.qtip.min.js'))
        css = {'all': (static_url('css/jquery.qtip.min.css'),)}


class FileFieldDiff(BaseFieldDiff):
    """
    Simply renders links to the two versions of the file.
    """
    template = 'diff/file_diff.html'

    _rough_type_map = [(r'^audio', 'audio'),
                       (r'^video', 'video'),
                       (r'^application/pdf', 'pdf'),
                       (r'^application/msword', 'word'),
                       (r'^text/html', 'html'),
                       (r'^text', 'text'),
                       (r'^image', 'image'),
                       (r'^application/vnd.ms-powerpoint', 'powerpoint'),
                       (r'^application/vnd.ms-excel', 'excel')
    ]

    def _get_rough_type(self):
        mime_type = mimetypes.guess_type(self.field1.name)[0]
        rough_type = None
        if mime_type:
            for regex, rough_type in self._rough_type_map:
                if re.match(regex, mime_type):
                    return rough_type
        return None

    def get_diff(self):
        """
        Returns a dictionary of all the file attributes or None if it's the
        same file.
        """
        if self.field1 == self.field2:
            return None

        diff = {
            'deleted': self.field1,
            'inserted': self.field2,
            'file_rough_type': self._get_rough_type(),
        }
        return diff

    def as_html(self):
        d = self.get_diff()
        if d is None:
            return '<tr><td colspan="2">(No differences found)</td></tr>'
        return render_to_string(self.template, {'diff': d})


class ImageFieldDiff(FileFieldDiff):
    """
    Compares the fields as image file paths and renders the images.
    """
    template = 'diff/image_diff.html'

    def as_html(self):
        d = self.get_diff()
        if d is None:
            return '<tr><td colspan="2">(No differences found)</td></tr>'
        return render_to_string(self.template, {'diff': d})


def get_diff_operations(a, b):
    """
    Returns the minimal diff operations between two strings, using difflib.
    """
    if a == b:
        return None
    operations = []
    sequence_matcher = difflib.SequenceMatcher(None, a, b)
    for opcode in sequence_matcher.get_opcodes():

        operation, start_a, end_a, start_b, end_b = opcode

        deleted = ''.join(a[start_a:end_a])
        inserted = ''.join(b[start_b:end_b])
        if operation == 'equal':
            operations.append({'equal': inserted})
        else:
            operations.append({'deleted': deleted,
                                'inserted': inserted})
    return operations


def get_diff_operations_clean(a, b):
    """
    Returns a cleaned-up, more human-friendly set of diff operations between
    two strings.  Uses diff_match_patch.
    """
    if a == b:
        return None
    dmp = diff_match_patch.diff_match_patch()
    dmp.Diff_Timeout = 0.01
    dmp.Diff_EditCost = 4

    diff = dmp.diff_main(a, b, False)
    dmp.diff_cleanupSemantic(diff)
    op_map = {diff_match_patch.diff_match_patch.DIFF_DELETE: 'deleted',
              diff_match_patch.diff_match_patch.DIFF_EQUAL: 'equal',
              diff_match_patch.diff_match_patch.DIFF_INSERT: 'inserted'
             }
    return [{op_map[op]: data} for op, data in diff]


class Registry(object):
    """
    This tracks what diff util should be used for what model or field.
    """
    def __init__(self):
        self._registry = {}

    def register(self, model_or_field, diff_util):
        """
        Registers a diff util for a particular model or field type.

        For convience, several built-in fields (CharField, TextField,
        FileField, ImageField) are pre-registered.

        NOTE: You generally don't have to register models to use diff() on
              them.  Registering a diff util for a field or model will give
              you the ability to customize behavior or deal with custom
              fields.

        Attrs:
            model_or_field: The type that will be compared (subclass of
                Model or Field)
            diff_util: The class that will do the comparison (subclass
                of BaseModelDiff or BaseFieldDiff, respectively)
        """
        self._registry[model_or_field] = diff_util

    def get_diff_util(self, model_or_field):
        if model_or_field in self._registry:
            return self._registry[model_or_field]
        if model_or_field is models.ForeignKey:
            return BaseModelDiff
        if model_or_field is models.Model:
            return BaseModelDiff
        if model_or_field is models.Field:
            return BaseFieldDiff
        # unregistered, try the base class
        if model_or_field.__base__ is not object:
            # NOTE: I think __base__ will grab the 'right' parent class.
            # This will probably work fine.  The work around
            # (for c in __bases__) is probably too annoying to implement.
            return self.get_diff_util(model_or_field.__base__)

        raise DiffUtilNotFound

registry = Registry()


def register(model_or_field, diff_util):
    """
    Registers a diff util for a particular model or field type.

    For convenience, several built-in fields (CharField, TextField,
    FileField, ImageField) are pre-registered.

    Examples::

        register(models.CharField, TextFieldDiff)
        register(MyModel, MyModelDiff)

    Attrs:
        model_or_field: The type that will be compared (subclass of
            Model or Field)
        diff_util: The class that will do the comparison (subclass
            of BaseModelDiff or BaseFieldDiff, respectively)
    """
    registry.register(model_or_field, diff_util)


def diff(object1, object2):
    """
    Compares two objects (such as model instances) and returns an object that
    can be used to render the differences between the two objects.

    Example::

        >>> m1 = Person(name="Philip")
        >>> m2 = Person(name="Phillip")
        >>> diff(m1, m2).as_dict()
        {'name': [{'equal': 'Phil'}, {'inserted': 'l'}, {'equal': 'ip'}]}
        >>> diff(m1, m2).as_html()
        u('<tr>'
            '<td colspan="2">name</td>'
          '</tr>
          '<tr>'
          '<td colspan="2">'
            '<span class="diff_equal">Phil</span>'
            '<ins>l</ins>'
            '<span class="diff_equal">ip</span>'
          '</td>
          '</tr>')

    This can work with versioned models, e.g.::

        >> diff(m1.versions.as_of(version=2),
        >>      m2.versions.as_of(version=3)).as_html()
        u('<tr>'
            '<td colspan="2">name</td>'
          '</tr>
          '<tr>'
          '<td colspan="2">'
            '<span class="diff_equal">Phil</span>'
            '<ins>l</ins>'
            '<span class="diff_equal">ip!</span>'
          '</td>
          '</tr>')

    Returns:
        An object that can be used to display differences.  Object will be
        either BaseModelDiff or a subclass.

    Raises:
        DiffUtilNotFound: If there's no registered or inferred diff for
        the objects.
    """
    if is_historical_instance(object1):
        base_class = object1.version_info._object.__class__
    else:
        base_class = object1.__class__

    diff_util = registry.get_diff_util(base_class)
    return diff_util(object1, object2, model_class=base_class)


# Built-in diff utils provided for some of the Django field types.
register(models.CharField, TextFieldDiff)
register(models.TextField, TextFieldDiff)
register(models.FileField, FileFieldDiff)
register(models.ImageField, ImageFieldDiff)
