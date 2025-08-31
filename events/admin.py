import copy
import datetime
from collections import defaultdict

from dateutil import rrule
from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.admin import widgets as admin_widgets
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.utils.html import format_html
from googleapiclient.discovery import build

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
        for field in ("opener", "closer"):
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
                    "start_time",
                    "end_time",
                    "all_day",
                    "location",
                    "details",
                    "is_break",
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
    list_display = ("title", "description", "event_type", "register_link")
    list_filter = ("event_type",)
    search_fields = ("title", "description")
    inlines = [OccurrenceInline]
    form = RecurringEventForm
    save_on_top = True
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

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:event_id>/attendance-register/",
                self.admin_site.admin_view(self.attendance_register),
                name="event_attendance_register",
            ),
            path(
                "<int:event_id>/attendance-register/export/",
                self.admin_site.admin_view(self.export_register),
                name="event_attendance_register_export",
            ),
        ]
        return custom_urls + urls

    def register_link(self, obj):
        return format_html(
            '<a href="{}">View register</a>',
            reverse("admin:event_attendance_register", args=[obj.pk]),
        )

    def get_register_context(self, event_id):
        event = get_object_or_404(Event, pk=event_id)
        occurrences = list(event.occurrence_set.order_by("start_time").all())

        # Get all attendance records for this event's occurrences
        attendance_qs = Occurrence.attendees.through.objects.filter(
            occurrence_id__event=event
        ).select_related("user")  # , 'occurrence')

        attendee_dict = {}
        occurrence_attendance = defaultdict(int)
        attendance_map = defaultdict(set)
        for record in attendance_qs:
            attendee_dict[record.user_id] = record.user
            attendance_map[record.user_id].add(record.occurrence_id)
            occurrence_attendance[record.occurrence_id] += 1

        attendees = sorted(
            attendee_dict.values(), key=lambda u: (u.last_name, u.first_name)
        )
        # Build attendance matrix
        attendance = [
            (
                attendee.get_full_name() or attendee.username,
                [
                    occ.id in (attended := attendance_map.get(attendee.id, set()))
                    for occ in occurrences
                ],
                len(attended),
            )
            for attendee in attendees
        ]
        return {
            "event": event,
            "occurrences": occurrences,
            "attendance": attendance,
            "counts": [occurrence_attendance[occ.id] for occ in occurrences],
        }

    def attendance_register(self, request, event_id):
        context = self.get_register_context(event_id)
        return render(
            request,
            "events/attendance_register.html",
            {
                "title": "Attendance",
                "opts": self.model._meta,
                **admin.site.each_context(request),
                **context,
            },
        )

    def export_register(self, request, event_id):
        if not request.POST:
            return redirect("admin:event_attendance_register", event_id=event_id)
        sheet_id = request.POST.get("sheet_id")
        request.session["sheet_id"] = sheet_id
        context = self.get_register_context(event_id)
        event = context["event"]
        occurrences = context["occurrences"]
        attendance = context["attendance"]

        header = [
            occ.details or "Break"
            if occ.is_break
            else occ.start_time.strftime("%Y-%m-%d")
            for occ in occurrences
        ]
        header_row = ["Attendee", *header, "Total"]

        data_rows = []
        for i, (attendee_name, attended_list, _) in enumerate(attendance):
            row = ["Y" if attended else "" for attended in attended_list]
            total = '=COUNTIF(B{row}:{end}{row}, "Y")'.format(
                row=i + 2, end=chr(ord("B") + len(occurrences) - 1)
            )
            data_rows.append([attendee_name, *row, total])

        totals = [
            '=COUNTIF({col}2:{col}{end}, "Y")'.format(
                col=chr(ord("B") + i), end=len(attendance)
            )
            for i, _ in enumerate(occurrences)
        ]
        total_row = ["Total", *totals]

        sheet_title = event.full_description
        values = [header_row, *data_rows, total_row]

        service = build("sheets", "v4", credentials=settings.GS_CREDENTIALS)
        sheets = service.spreadsheets()

        spreadsheet = sheets.get(spreadsheetId=sheet_id).execute()
        existing_sheet = None
        for sheet in spreadsheet.get("sheets", []):
            if sheet["properties"]["title"].lower() == sheet_title.lower():
                existing_sheet = sheet
                break

        if existing_sheet:
            sheets.values().clear(
                spreadsheetId=sheet_id,
                range=f"'{sheet_title}'",
            ).execute()
        else:
            add_sheet_request = {
                "addSheet": {"properties": {"title": sheet_title, "index": 0}}
            }
            response = sheets.batchUpdate(
                spreadsheetId=sheet_id, body={"requests": [add_sheet_request]}
            ).execute()
            sheet_title = response["replies"][0]["addSheet"]["properties"]["title"]

        sheets.values().update(
            spreadsheetId=sheet_id,
            range=f"'{sheet_title}'!A1",
            valueInputOption="USER_ENTERED",
            body={"values": values},
        ).execute()
        return redirect("admin:event_attendance_register", event_id=event.id)


@admin.register(Occurrence)
class OccurrenceAdmin(admin.ModelAdmin):
    list_display = ("__str__", "start_time", "end_time", "all_day", "location", "event")
    list_filter = ("event",)
    search_fields = ("event__title",)
    date_hierarchy = "start_time"
    filter_horizontal = ("attendees",)
