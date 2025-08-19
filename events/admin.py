import datetime

from dateutil import rrule
from django import forms
from django.contrib import admin, messages
from django.contrib.admin import widgets as admin_widgets
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from django.utils.html import format_html

from events.models import Event, EventType, Occurrence

WEEKDAY_LONG = (
    (7, "Sunday"),
    (1, "Monday"),
    (2, "Tuesday"),
    (3, "Wednesday"),
    (4, "Thursday"),
    (5, "Friday"),
    (6, "Saturday"),
)


ISO_WEEKDAYS_MAP = (
    None,
    rrule.MO,
    rrule.TU,
    rrule.WE,
    rrule.TH,
    rrule.FR,
    rrule.SA,
    rrule.SU,
)


@admin.register(EventType)
class EventTypeAdmin(admin.ModelAdmin):
    pass


class RecurringEventForm(forms.ModelForm):
    start_time = forms.SplitDateTimeField(
        widget=admin_widgets.AdminSplitDateTime(),
        help_text="The start date and time of the first occurrence to be added",
        required=False,
    )
    end_time = forms.TimeField(
        widget=admin_widgets.AdminTimeWidget(),
        help_text="The end time of the first occurrence to be added",
        required=False,
    )
    count = forms.IntegerField(
        help_text="The number of occurrences to be added", required=False
    )
    until = forms.DateField(
        help_text="The date of the last occurrence to be added",
        widget=admin_widgets.AdminDateWidget(),
        required=False,
    )
    days = forms.TypedMultipleChoiceField(
        choices=WEEKDAY_LONG,
        help_text="The days of the week the event occurs on",
        widget=forms.CheckboxSelectMultiple,
        coerce=int,
        required=False,
    )
    location = forms.CharField(
        max_length=255,
        help_text="The location of the event",
        required=False,
    )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("count") and cleaned_data.get("until"):
            raise forms.ValidationError(
                "You can't specify both a count and an end date"
            )
        if cleaned_data.get("start_time") and cleaned_data.get("end_time"):
            cleaned_data['end'] = datetime.datetime.combine(
                cleaned_data["start_time"].date(),
                cleaned_data["end_time"],
                cleaned_data["start_time"].tzinfo,
            )
        if cleaned_data.get("until"):
            cleaned_data['until'] = datetime.datetime.combine(
                cleaned_data["until"],
                cleaned_data["end_time"],
                cleaned_data["start_time"].tzinfo,
            )
        return cleaned_data


class OccurrenceInline(admin.TabularInline):
    model = Occurrence
    extra = 1
    fields = ("start_time", "end_time", "location", "all_day", "details")


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "description", "event_type", "add_occurence_link")
    list_filter = ("event_type",)
    search_fields = ("title", "description")
    inlines = [OccurrenceInline]
    form = RecurringEventForm
    fieldsets = (
        (None, {"fields": ("title", "description", "event_type", "details")}),
        (
            "Recurring Event",
            {
                "fields": (
                    "start_time",
                    "end_time",
                    "count",
                    "until",
                    "days",
                    "location",
                )
            },
        ),
    )

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
                    end_time=form.cleaned_data["end"],
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


@admin.register(Occurrence)
class OccurrenceAdmin(admin.ModelAdmin):
    list_display = ("__str__", "start_time", "end_time", "event")
    list_filter = ("event",)
    search_fields = ("event__title",)
    date_hierarchy = "start_time"
