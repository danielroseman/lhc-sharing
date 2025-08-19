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


@register.inclusion_tag("swingtime/event_notes.html")
def event_notes(occurrence):
    return {
        "occurrence": occurrence,
        "notes": occurrence.notes.all(),
        "event_notes": occurrence.event.notes.all(),
    }
