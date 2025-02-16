from direct_cloud_upload import CloudFileWidget, DdcuAdminMixin
from django import forms
from django.contrib import admin, messages
from django.contrib.contenttypes.admin import GenericTabularInline
from django.contrib.flatpages.admin import FlatPageAdmin
from django.contrib.flatpages.models import FlatPage
from django.db import models
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from django.utils.html import format_html
from swingtime.admin import EventAdmin
from swingtime.forms import ISO_WEEKDAYS_MAP, WEEKDAY_LONG
from swingtime.models import Event, Note, Occurrence

from music.models import DDCU_BUCKET_IDENTIFIER, Song


class SongForm(forms.ModelForm):
    class Meta:
        model = Song
        fields = ["name", "slug", "created_at", "current", "files"]

        widgets = {
            "files": CloudFileWidget(
                bucket_identifier=DDCU_BUCKET_IDENTIFIER,
                path_prefix="media/",
                include_timestamp=False,
                allow_multiple=True,
            )
        }


@admin.register(Song)
class SongAdmin(DdcuAdminMixin):
    list_display = ("name", "current")
    list_editable = ["current"]
    form = SongForm
    prepopulated_fields = {"slug": ["name"]}


admin.site.unregister(Event)


class RecurringEventForm(forms.Form):
    start_time = forms.SplitDateTimeField(
        widget=admin.widgets.AdminSplitDateTime(),
        help_text="The start time of the first occurrence to be added",
    )
    end_time = forms.SplitDateTimeField(
        widget=admin.widgets.AdminSplitDateTime(),
        help_text="The end time of the first occurrence to be added",
    )
    count = forms.IntegerField(
        help_text="The number of occurrences to be added", required=False
    )
    until = forms.DateField(
        help_text="The date of the last occurrence to be added",
        widget=admin.widgets.AdminDateWidget(),
        required=False,
    )
    days = forms.TypedMultipleChoiceField(
        choices=WEEKDAY_LONG,
        help_text="The days of the week the event occurs on",
        widget=forms.CheckboxSelectMultiple,
        coerce=int,
    )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("count") and cleaned_data.get("until"):
            raise forms.ValidationError(
                "You can't specify both a count and an end date"
            )
        return cleaned_data


@admin.register(Event)
class EventAdmin(EventAdmin):
    list_display = EventAdmin.list_display + ("add_occurence_link",)

    def add_occurence_link(self, obj):
        return format_html(
            '<a href="{}">Add occurrences</a>',
            reverse("admin:event_add_occurrences", args=[obj.pk]),
        )

    def add_occurrences(self, request, event_id):
        event = get_object_or_404(Event, pk=event_id)
        if request.method == "POST":
            form = RecurringEventForm(request.POST)
            if form.is_valid():
                count_before = event.occurrence_set.count()
                event.add_occurrences(
                    start_time=form.cleaned_data["start_time"],
                    end_time=form.cleaned_data["end_time"],
                    count=form.cleaned_data.get("count"),
                    until=form.cleaned_data.get("until"),
                    byweekday=[
                        ISO_WEEKDAYS_MAP[day] for day in form.cleaned_data["days"]
                    ],
                )
                count_added = event.occurrence_set.count() - count_before
                msg = format_html(
                    "{count} occurrences added successfully to {obj}",
                    obj=event,
                    count=count_added,
                )
                self.message_user(request, msg, messages.SUCCESS)
                return self.response_post_save_change(request, event)
        else:
            form = RecurringEventForm()
        admin_form = admin.helpers.AdminForm(
            form, [(None, {"fields": form.fields})], {}
        )
        context = dict(
            self.admin_site.each_context(request),
            opts=self.opts,
            event=event,
            adminform=admin_form,
            errors=admin.helpers.AdminErrorList(form, []),
            title="Add occurrences",
            subtitle=str(event),
            original=event,
            media=self.media + admin_form.media,
            inline_admin_formsets=[],
        )
        return self.render_change_form(request, context, change=True)

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                "<int:event_id>/add_occurrences/",
                self.add_occurrences,
                name="event_add_occurrences",
            ),
        ]
        return my_urls + urls


class OccurrenceNoteInline(GenericTabularInline):
    model = Note
    extra = 1


@admin.register(Occurrence)
class OccurrenceAdmin(admin.ModelAdmin):
    list_display = ("__str__", "start_time", "end_time", "event")
    list_filter = ("event",)
    search_fields = ("event__title",)
    date_hierarchy = "start_time"
    inlines = [OccurrenceNoteInline]


admin.site.unregister(FlatPage)

@admin.register(FlatPage)
class MarkdownxFlatPageAdmin(FlatPageAdmin):
    class Media:
        css = {"all": ("https://unpkg.com/tiny-markdown-editor/dist/tiny-mde.min.css",)}
        js = (
            "https://unpkg.com/tiny-markdown-editor/dist/tiny-mde.min.js",
        )


