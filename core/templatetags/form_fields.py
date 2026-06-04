from django import forms
from django import template

register = template.Library()


@register.filter
def is_select_field(field):
    widget = field.field.widget
    return isinstance(widget, forms.Select) and not isinstance(
        widget, (forms.SelectMultiple, forms.CheckboxSelectMultiple)
    )


@register.filter
def is_multi_checkbox_field(field):
    return isinstance(field.field.widget, forms.CheckboxSelectMultiple)


@register.filter
def is_file_image_field(field):
    if getattr(field.field.widget, 'input_type', None) != 'file':
        return False
    return isinstance(field.field, forms.ImageField)


@register.filter
def select_field_options(field):
    options = []
    for value, label in field.field.choices:
        options.append(('' if value is None else str(value), label))
    return options
