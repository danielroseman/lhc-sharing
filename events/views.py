import calendar
import itertools
from datetime import datetime, timedelta

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
    queryset = Occurrence.objects.select_related()
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
    occurrences = event.occurrence_set.filter(start_time__gte=timezone.now())
    return render(
        request,
        "events/occurrence_grid_signup.html",
        {"event": event, "occurrences": occurrences},
    )


@login_required
def occurrence_printable_schedule(request, event_id):
    """
    Display a printable schedule of occurrences for an event,
    grouped by month with opener/closer assignments and comments.
    Includes detection of weeks without rehearsals.
    """
    event = Event.objects.get(id=event_id)
    occurrences = list(
        event.occurrence_set.filter(start_time__gte=timezone.now()).order_by(
            "start_time"
        )
    )

    if not occurrences:
        return render(
            request,
            "events/occurrence_printable_schedule.html",
            {"event": event, "grouped_occurrences": {}},
        )

    # Create a set of all weeks that have rehearsals
    rehearsal_weeks = set()
    for occurrence in occurrences:
        # Get the Monday of the week for this occurrence
        week_start = occurrence.start_time.date() - timedelta(
            days=occurrence.start_time.weekday()
        )
        rehearsal_weeks.add(week_start)

    # Generate all weeks from first to last occurrence
    first_date = occurrences[0].start_time.date()
    last_date = occurrences[-1].start_time.date()

    # Start from the Monday of the first week
    current_week = first_date - timedelta(days=first_date.weekday())
    last_week = last_date - timedelta(days=last_date.weekday())

    # Create entries for all weeks, marking those without rehearsals
    all_entries = []

    for occurrence in occurrences:
        all_entries.append({
            "type": "rehearsal",
            "date": occurrence.start_time,
            "occurrence": occurrence,
        })

    # Add "no rehearsal" entries for weeks without rehearsals
    while current_week <= last_week:
        if current_week not in rehearsal_weeks:
            # Use Tuesday of the week (typical rehearsal day) for both sorting and display
            week_tuesday = current_week + timedelta(days=1)  # Tuesday
            week_sunday = current_week + timedelta(days=6)  # Sunday (end of week)

            # Use Tuesday for sorting and display (as rehearsals are typically on Tuesdays)
            sort_date = datetime.combine(week_tuesday, datetime.min.time())
            sort_date = timezone.make_aware(sort_date, timezone.get_current_timezone())

            all_entries.append({
                "type": "no_rehearsal",
                "date": sort_date,  # Used for sorting (Tuesday)
                "week_start": current_week,  # Monday
                "week_end": week_sunday,  # Sunday
                "display_date": week_tuesday,  # Display Tuesday (typical rehearsal day)
            })
        current_week += timedelta(weeks=1)

    # Sort all entries by date
    all_entries.sort(key=lambda x: x["date"])

    # Group all entries by month and assign month indices
    grouped_occurrences = {}
    month_classes = {}
    month_index = 0

    for entry in all_entries:
        month_key = entry["date"].strftime("%B %Y")
        if month_key not in grouped_occurrences:
            grouped_occurrences[month_key] = []
            # Assign a class index to this month (month-1, month-2, month-3)
            month_classes[month_key] = f"month-{month_index % 3 + 1}"
            month_index += 1
        grouped_occurrences[month_key].append(entry)

    return render(
        request,
        "events/occurrence_printable_schedule.html",
        {
            "event": event,
            "grouped_occurrences": grouped_occurrences,
            "month_classes": month_classes,
        },
    )
