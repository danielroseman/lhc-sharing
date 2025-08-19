import calendar
import itertools
from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from events.models import Occurrence


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

    by_day = dict(
        [(dt, list(o)) for dt, o in itertools.groupby(occurrences, start_day)]
    )
    data = {
        "today": datetime.now(),
        "calendar": [[(d, by_day.get(d, [])) for d in row] for row in cal],
        "this_month": dtstart,
        "next_month": dtstart + timedelta(days=+last_day),
        "last_month": dtstart + timedelta(days=-1),
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
