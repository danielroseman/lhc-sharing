import markdown as md
from django.template import Library
from django.utils.safestring import mark_safe

register = Library()


@register.filter
def readable_name(value):
    return value.replace("_", " ")


@register.filter
def markdown(value):
    return mark_safe(md.markdown(value))
