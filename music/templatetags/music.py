from django.template import Library

register = Library()

@register.filter
def readable_name(value):
    return value.replace("_", " ")
