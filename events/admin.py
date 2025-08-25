import copy
import datetime

from dateutil import rrule
from django import forms
from django.contrib import admin
from django.contrib.admin import widgets as admin_widgets

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

    class Meta:
        model = Event
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        if any(
            cleaned_data.get(field)
            for field in ["start_time", "end_time", "days", "count", "until"]
        ):
            if (
                not cleaned_data.get("start_time")
                or not cleaned_data.get("end_time")
                or not cleaned_data.get("days")
                or (not cleaned_data.get("count") and not cleaned_data.get("until"))
            ):
                raise forms.ValidationError(
                    "To create recurring events you must specify a start time, end "
                    "time, days of the week, and either a count or an until date."
                )

        if cleaned_data.get("count") and cleaned_data.get("until"):
            raise forms.ValidationError(
                "You can't specify both a count and an end date"
            )
        if cleaned_data.get("start_time") and cleaned_data.get("end_time"):
            cleaned_data["end"] = datetime.datetime.combine(
                cleaned_data["start_time"].date(),
                cleaned_data["end_time"],
                cleaned_data["start_time"].tzinfo,
            )
        if cleaned_data.get("until"):
            cleaned_data["until"] = datetime.datetime.combine(
                cleaned_data["until"],
                cleaned_data["end_time"],
                cleaned_data["start_time"].tzinfo,
            )

        return cleaned_data


class InlineOccurrenceForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ('opener', 'closer'):
            self.fields[field].widget.can_add_related = False
            self.fields[field].widget.can_change_related = False
            self.fields[field].widget.can_delete_related = False


class OccurrenceInline(admin.StackedInline):
    model = Occurrence
    extra = 1
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "start_time", "end_time", "all_day",
                    "location", "details",
                ),
                "classes": ["grid-layout"],
            },
        ),
        (
            None,
            {
                "fields": (("opener", "closer"),),
            },
        ),
    )
    form = InlineOccurrenceForm


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "description", "event_type")
    list_filter = ("event_type",)
    search_fields = ("title", "description")
    inlines = [OccurrenceInline]
    form = RecurringEventForm
    fieldsets = (
        (None, {"fields": ("title", "description", "event_type", "details")}),
        (
            "Add recurring event",
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

    def get_fieldsets(self, request, obj=None):
        fieldsets = copy.deepcopy(super().get_fieldsets(request, obj))
        if obj and obj.occurrence_set.exists():
            # If the event already has occurrences, collapse the recurring event fields
            fieldsets[1][1]["classes"] = ["collapse"]
        return fieldsets

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if form.cleaned_data.get("start_time") and form.cleaned_data.get("end_time"):
            obj.add_occurrences(
                start_time=form.cleaned_data["start_time"],
                end_time=form.cleaned_data["end"],
                count=form.cleaned_data.get("count"),
                until=form.cleaned_data.get("until"),
                byweekday=[ISO_WEEKDAYS_MAP[day] for day in form.cleaned_data["days"]],
                location=form.cleaned_data.get("location", ""),
            )


@admin.register(Occurrence)
class OccurrenceAdmin(admin.ModelAdmin):
    list_display = ("__str__", "start_time", "end_time", "all_day", "location", "event")
    list_filter = ("event",)
    search_fields = ("event__title",)
    date_hierarchy = "start_time"
