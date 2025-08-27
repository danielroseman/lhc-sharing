from datetime import datetime
from datetime import timezone as datetime_timezone
from unittest import mock

import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

from events.models import Event, EventType, Occurrence


@pytest.fixture
def user(db):
    return User.objects.create_user(username="testuser", password="pass")


@pytest.fixture
def event_type(db):
    return EventType.objects.create(label="Rehearsal")


@pytest.fixture
def event(db, event_type):
    return Event.objects.create(
        title="Fall Rehearsals",
        event_type=event_type,
    )


def test_missing_week_detection_october_28(client, user, event):
    """
    Test that missing week on Oct 28 is correctly detected between Oct 21 and Nov 4.
    """
    current_tz = timezone.get_current_timezone()

    # Create occurrences on Oct 21 and Nov 4
    Occurrence.objects.create(
        event=event,
        start_time=datetime(2025, 10, 21, 19, 0, tzinfo=current_tz),
        end_time=datetime(2025, 10, 21, 21, 0, tzinfo=current_tz),
    )
    Occurrence.objects.create(
        event=event,
        start_time=datetime(2025, 11, 4, 19, 0, tzinfo=current_tz),
        end_time=datetime(2025, 11, 4, 21, 0, tzinfo=current_tz),
    )

    url = reverse("occurrence_printable_schedule", args=[event.id])

    # Mock the date BEFORE logging in to avoid session expiry issues
    with mock.patch("django.utils.timezone.now") as mock_now:
        mock_now.return_value = datetime(
            2025, 10, 1, 10, 0, 0, tzinfo=datetime_timezone.utc
        )

        # Login within the mocked time context
        client.force_login(user)

        response = client.get(url)

    assert response.status_code == 200
    all_entries = response.context["entries"]

    # Find the no-rehearsal entry
    no_rehearsal_entries = [e for e in all_entries if e["type"] == "no_rehearsal"]

    # Should be exactly one missing week (Oct 27 - Nov 2)
    assert len(no_rehearsal_entries) == 1

    # The missing week is Oct 27 - Nov 2 (contains Oct 28 which has no rehearsal)
    missing_week = no_rehearsal_entries[0]
    assert missing_week["week_start"].day == 27
    assert missing_week["week_start"].month == 10
    assert missing_week["week_end"].day == 2
    assert missing_week["week_end"].month == 11

    # Verify the displayed date (Tuesday of that week = Oct 28)
    assert missing_week["display_date"].day == 28
    assert missing_week["display_date"].month == 10


def test_multiple_missing_weeks(client, user, event):
    """Test detection of multiple missing weeks."""
    current_tz = timezone.get_current_timezone()

    # Create occurrences with 2-week gaps
    Occurrence.objects.create(
        event=event,
        start_time=datetime(2025, 10, 7, 19, 0, tzinfo=current_tz),
        end_time=datetime(2025, 10, 7, 21, 0, tzinfo=current_tz),
    )
    Occurrence.objects.create(
        event=event,
        start_time=datetime(2025, 10, 28, 19, 0, tzinfo=current_tz),
        end_time=datetime(2025, 10, 28, 21, 0, tzinfo=current_tz),
    )
    Occurrence.objects.create(
        event=event,
        start_time=datetime(2025, 11, 18, 19, 0, tzinfo=current_tz),
        end_time=datetime(2025, 11, 18, 21, 0, tzinfo=current_tz),
    )

    url = reverse("occurrence_printable_schedule", args=[event.id])

    with mock.patch("django.utils.timezone.now") as mock_now:
        mock_now.return_value = datetime(
            2025, 10, 1, 10, 0, 0, tzinfo=datetime_timezone.utc
        )
        client.force_login(user)
        response = client.get(url)

    assert response.status_code == 200
    all_entries = response.context["entries"]

    # Find no-rehearsal entries
    no_rehearsal_entries = [e for e in all_entries if e["type"] == "no_rehearsal"]

    # Should be exactly 3 missing weeks (Oct 14, Oct 21, Nov 4, Nov 11)
    assert len(no_rehearsal_entries) == 4

    # Check the dates of missing weeks (Sundays)
    missing_sundays = sorted([
        e["week_end"].day for e in no_rehearsal_entries if e["week_end"].month == 10
    ])
    assert missing_sundays == [
        12,
        19,
    ]  # Oct 12 and Oct 19 are the Sundays of missing weeks

    missing_sundays_nov = sorted([
        e["week_end"].day for e in no_rehearsal_entries if e["week_end"].month == 11
    ])
    assert missing_sundays_nov == [
        2,
        9,
    ]  # Nov 2 and Nov 9 are the Sundays of missing weeks


def test_consecutive_weeks_no_gap(client, user, event):
    """Test that consecutive weeks don't show as missing."""
    current_tz = timezone.get_current_timezone()

    # Create occurrences every week
    Occurrence.objects.create(
        event=event,
        start_time=datetime(2025, 10, 7, 19, 0, tzinfo=current_tz),
        end_time=datetime(2025, 10, 7, 21, 0, tzinfo=current_tz),
    )
    Occurrence.objects.create(
        event=event,
        start_time=datetime(2025, 10, 14, 19, 0, tzinfo=current_tz),
        end_time=datetime(2025, 10, 14, 21, 0, tzinfo=current_tz),
    )
    Occurrence.objects.create(
        event=event,
        start_time=datetime(2025, 10, 21, 19, 0, tzinfo=current_tz),
        end_time=datetime(2025, 10, 21, 21, 0, tzinfo=current_tz),
    )

    url = reverse("occurrence_printable_schedule", args=[event.id])

    with mock.patch("django.utils.timezone.now") as mock_now:
        mock_now.return_value = datetime(
            2025, 10, 1, 10, 0, 0, tzinfo=datetime_timezone.utc
        )
        client.force_login(user)
        response = client.get(url)

    assert response.status_code == 200
    all_entries = response.context["entries"]

    # Find no-rehearsal entries
    no_rehearsal_entries = [e for e in all_entries if e["type"] == "no_rehearsal"]

    # Should be no missing weeks
    assert len(no_rehearsal_entries) == 0
