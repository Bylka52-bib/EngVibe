from django import template
from django.utils.safestring import mark_safe

from core.lesson_html import sanitize_lesson_html

register = template.Library()


@register.filter(name='lesson_html')
def lesson_html(value):
    return mark_safe(sanitize_lesson_html(value))
