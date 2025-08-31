import calendar
import itertools
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from events.models import Event, Occurrence


@login_required
def month_view_notes(request, year, month):
    year, month = int(year), int(month)
    cal = calendar.monthcalendar(year, month)
    dtstart = datetime(year, month, 1)
    last_day = max(cal[-1])

    # TODO Whether to include those occurrences that started in the previous
    # month but end in this month?
    queryset = Occurrence.objects.exclude(is_break=True).select_related(
        "opener", "closer", "event"
    )
    occurrences = queryset.filter(start_time__year=year, start_time__month=month)
    current_timezone = timezone.get_current_timezone()

    def start_day(o):
        return o.start_time.astimezone(current_timezone).day

    by_day = dict([
        (dt, list(o)) for dt, o in itertools.groupby(occurrences, start_day)
    ])
    data = {
        "today": timezone.now(),
        "calendar": [[(d, by_day.get(d, [])) for d in row] for row in cal],
        "this_month": dtstart,
        "next_month": dtstart + timedelta(days=+last_day),
        "last_month": dtstart + timedelta(days=-1),
        "occurrences": occurrences,
    }

    return render(request, "events/monthly_view.html", data)


@login_required
def event_occurrence(request, event_id, occurrence_id):
    occurrence = Occurrence.objects.select_related("event").get(
        id=occurrence_id, event__id=event_id
    )
    return render(
        request,
        "events/occurrence.html",
        {"occurrence": occurrence, "event": occurrence.event},
    )


@login_required
def occurrence_grid_signup(request, event_id):
    if request.method == "POST":
        occurrence_id = request.POST.get("occurrence_id")
        role = request.POST.get("role")  # 'opener' or 'closer'

        try:
            occurrence = Occurrence.objects.get(id=occurrence_id)
            if role == "opener" and occurrence.opener is None:
                occurrence.opener = request.user
                occurrence.save()
            elif role == "closer" and occurrence.closer is None:
                occurrence.closer = request.user
                occurrence.save()
        except Occurrence.DoesNotExist:
            pass

        return redirect("occurrence_signup_grid", event_id=event_id)

    event = Event.objects.get(id=event_id)
    occurrences = event.occurrence_set.filter(
        start_time__gte=timezone.now()
    ).select_related("opener", "closer")
    return render(
        request,
        "events/occurrence_grid_signup.html",
        {"event": event, "occurrences": occurrences},
    )


@login_required
def occurrence_printable_schedule(request, event_id):
    event = Event.objects.get(id=event_id)
    occurrences = (
        event.occurrence_set.filter(start_time__gte=timezone.now())
        .order_by("start_time")
        .select_related("opener", "closer")
    )
    return render(
        request,
        "events/occurrence_printable_schedule.html",
        {"event": event, "occurrences": occurrences},
    )


@login_required
def mark_attendance(request):
    if request.method == "POST":
        occurrence_id = request.POST.get("occurrence_id")
        try:
            occurrence = Occurrence.objects.get(id=occurrence_id)
            occurrence.attendees.add(request.user)
        except Occurrence.DoesNotExist:
            pass

        return redirect("mark_attendance_success", occurrence_id=occurrence_id)
    else:
        occurrence = Occurrence.objects.filter(
            start_time__date=timezone.now().date(), event__event_type__label="Rehearsal"
        ).first()
        if not occurrence:
            occurrence = Occurrence.objects.filter(
                start_time__gte=timezone.now(), event__event_type__label="Rehearsal"
            ).first()
        already_attended = False
        if occurrence and occurrence.attendees.filter(id=request.user.id).exists():
            already_attended = True
        return render(
            request,
            "events/mark_attendance.html",
            {"occurrence": occurrence, "already_attended": already_attended},
        )


@login_required
def mark_attendance_success(request, occurrence_id):
    occurrence = Occurrence.objects.get(id=occurrence_id)
    return render(request, "events/attendance_success.html", {"occurrence": occurrence})
