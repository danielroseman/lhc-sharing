from datetime import timedelta

import pytest
from dateutil import rrule
from django.contrib.auth import get_user_model
from django.utils import timezone

from events.models import Event, EventType, Occurrence

User = get_user_model()


@pytest.mark.django_db
def test_occurrence_str_and_properties():
    et = EventType.objects.create(label="Workshop")
    event = Event.objects.create(
        title="Python Workshop", event_type=et, details="Bring a laptop."
    )
    start_time = timezone.now()
    end_time = start_time + timedelta(hours=2)
    user = User.objects.create(username="alice", first_name="Alice", last_name="Smith")
    occurrence = Occurrence.objects.create(
        event=event,
        location="Lab A",
        start_time=start_time,
        end_time=end_time,
        details="Snacks included.",
        opener=user,
    )
    expected_str = f"{event.title} on {start_time.strftime('%Y-%m-%d %H:%M')}"
    assert str(occurrence) == expected_str
    assert occurrence.title == event.title
    assert occurrence.event_type == et
    assert "Bring a laptop." in occurrence.all_details
    assert "Lab A" in occurrence.all_details
    assert "Open: Alice Smith" in occurrence.all_details
    assert "Snacks included." in occurrence.all_details


@pytest.mark.django_db
def test_add_occurrences_single():
    et = EventType.objects.create(label="Single")
    event = Event.objects.create(title="Solo Event", event_type=et)
    start_time = timezone.now()
    end_time = start_time + timedelta(hours=1)
    event.add_occurrences(start_time, end_time, location="Room 1")
    assert event.occurrence_set.count() == 1
    occ = event.occurrence_set.first()
    assert occ.start_time == start_time
    assert occ.end_time == end_time
    assert occ.location == "Room 1"


@pytest.mark.django_db
def test_add_occurrences_rrule_count():
    et = EventType.objects.create(label="Repeat")
    event = Event.objects.create(title="Repeated Event", event_type=et)
    start_time = timezone.now()
    end_time = start_time + timedelta(hours=1)
    # Add 3 daily occurrences
    event.add_occurrences(
        start_time, end_time, location="Hall",
        freq=rrule.DAILY, count=3
    )
    assert event.occurrence_set.count() == 3
    times = sorted([o.start_time for o in event.occurrence_set.all()])
    assert times[1] - times[0] == timedelta(days=1)
    assert times[2] - times[1] == timedelta(days=1)


@pytest.mark.django_db
def test_add_occurrences_rrule_until():
    et = EventType.objects.create(label="RepeatUntil")
    event = Event.objects.create(title="Until Event", event_type=et)
    start_time = timezone.now()
    end_time = start_time + timedelta(hours=1)
    until = start_time + timedelta(days=2)
    event.add_occurrences(
        start_time, end_time, location="Library",
        freq=rrule.DAILY, until=until
    )
    # Should create 3 occurrences: today, +1 day, +2 days (inclusive of 'until')
    assert event.occurrence_set.count() == 3
    for occ in event.occurrence_set.all():
        assert occ.location == "Library"
        assert occ.end_time - occ.start_time == timedelta(hours=1)
