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
def other_user(db):
    return User.objects.create_user(username="otheruser", password="pass")


@pytest.fixture
def client_logged_in(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def event_type(db):
    return EventType.objects.create(label="Rehearsal")


@pytest.fixture
def event(db, event_type):
    return Event.objects.create(
        title="Summer Rehearsals",
        event_type=event_type,
    )


@pytest.fixture
def occurrences_august_2025(event):
    # Create occurrences in August 2025
    current_tz = timezone.get_current_timezone()
    occ1 = Occurrence.objects.create(
        event=event,
        start_time=datetime(2025, 8, 5, 10, 0, tzinfo=current_tz),
        end_time=datetime(2025, 8, 5, 12, 0, tzinfo=current_tz),
    )
    occ2 = Occurrence.objects.create(
        event=event,
        start_time=datetime(2025, 8, 15, 14, 0, tzinfo=current_tz),
        end_time=datetime(2025, 8, 15, 16, 0, tzinfo=current_tz),
    )
    occ3 = Occurrence.objects.create(
        event=event,
        start_time=datetime(2025, 8, 15, 18, 0, tzinfo=current_tz),  # Same day as occ2
        end_time=datetime(2025, 8, 15, 20, 0, tzinfo=current_tz),
    )
    return [occ1, occ2, occ3]


@pytest.fixture
def future_occurrences(event):
    # Create occurrences in the future relative to August 25, 2025
    current_tz = timezone.get_current_timezone()
    future1 = Occurrence.objects.create(
        event=event,
        start_time=datetime(2025, 8, 26, 10, 0, tzinfo=current_tz),
        end_time=datetime(2025, 8, 26, 12, 0, tzinfo=current_tz),
    )
    future2 = Occurrence.objects.create(
        event=event,
        start_time=datetime(2025, 9, 1, 14, 0, tzinfo=current_tz),
        end_time=datetime(2025, 9, 1, 16, 0, tzinfo=current_tz),
    )
    # Past occurrence
    past = Occurrence.objects.create(
        event=event,
        start_time=datetime(2025, 8, 20, 10, 0, tzinfo=current_tz),
        end_time=datetime(2025, 8, 20, 12, 0, tzinfo=current_tz),
    )
    return [future1, future2, past]


def test_month_view_notes_shows_calendar_with_occurrences(
    client_logged_in, occurrences_august_2025
):
    url = reverse("event-monthly-view", args=[2025, 8])
    response = client_logged_in.get(url)

    assert response.status_code == 200
    assert "calendar" in response.context
    assert "occurrences" in response.context

    # Check that all August 2025 occurrences are included
    occurrences = response.context["occurrences"]
    assert len(occurrences) == 3

    # Check calendar structure - should group occurrences by day
    calendar_grid = response.context["calendar"]
    # Find day 5 and day 15 in the calendar
    day_5_occurrences = None
    day_15_occurrences = None

    for week in calendar_grid:
        for day, day_occurrences in week:
            if day == 5:
                day_5_occurrences = day_occurrences
            elif day == 15:
                day_15_occurrences = day_occurrences

    assert len(day_5_occurrences) == 1  # One occurrence on day 5
    assert len(day_15_occurrences) == 2  # Two occurrences on day 15


def test_month_view_notes_navigation_dates(client_logged_in, occurrences_august_2025):
    url = reverse("event-monthly-view", args=[2025, 8])
    response = client_logged_in.get(url)

    context = response.context
    assert context["this_month"] == datetime(2025, 8, 1)
    # Next month should be September
    assert context["next_month"].month == 9
    assert context["next_month"].year == 2025
    # Last month should be July
    assert context["last_month"].month == 7
    assert context["last_month"].year == 2025


def test_occurrence_grid_signup_get_shows_future_occurrences(
    client_logged_in, event, future_occurrences
):
    url = reverse("occurrence_signup_grid", args=[event.id])

    with mock.patch("events.views.timezone.now") as mock_now:
        mock_now.return_value = datetime(
            2025, 8, 25, 10, 11, 7, tzinfo=datetime_timezone.utc
        )
        response = client_logged_in.get(url)

    assert response.status_code == 200
    occurrences = response.context["occurrences"]

    # Should only include future occurrences (future1 and future2, not past)
    assert len(occurrences) == 2
    occurrence_ids = [occ.id for occ in occurrences]
    assert future_occurrences[0].id in occurrence_ids  # future1
    assert future_occurrences[1].id in occurrence_ids  # future2
    assert future_occurrences[2].id not in occurrence_ids  # past


def test_occurrence_grid_signup_post_opener_success(
    client_logged_in, event, future_occurrences, user
):
    occ = future_occurrences[0]
    assert occ.opener is None

    url = reverse("occurrence_signup_grid", args=[event.id])
    response = client_logged_in.post(url, {"occurrence_id": occ.id, "role": "opener"})

    occ.refresh_from_db()
    assert occ.opener == user
    assert response.status_code == 302
    assert response.url == reverse("occurrence_signup_grid", args=[event.id])


def test_occurrence_grid_signup_post_closer_success(
    client_logged_in, event, future_occurrences, user
):
    occ = future_occurrences[1]
    assert occ.closer is None

    url = reverse("occurrence_signup_grid", args=[event.id])
    response = client_logged_in.post(url, {"occurrence_id": occ.id, "role": "closer"})

    occ.refresh_from_db()
    assert occ.closer == user
    assert response.status_code == 302


def test_occurrence_grid_signup_post_opener_already_taken(
    client_logged_in, event, future_occurrences, user, other_user
):
    occ = future_occurrences[0]
    occ.opener = other_user
    occ.save()

    url = reverse("occurrence_signup_grid", args=[event.id])
    response = client_logged_in.post(url, {"occurrence_id": occ.id, "role": "opener"})

    occ.refresh_from_db()
    assert occ.opener == other_user  # Should not change
    assert response.status_code == 302


def test_occurrence_grid_signup_post_closer_already_taken(
    client_logged_in, event, future_occurrences, user, other_user
):
    occ = future_occurrences[0]
    occ.closer = other_user
    occ.save()

    url = reverse("occurrence_signup_grid", args=[event.id])
    response = client_logged_in.post(url, {"occurrence_id": occ.id, "role": "closer"})

    occ.refresh_from_db()
    assert occ.closer == other_user  # Should not change
    assert response.status_code == 302


def test_occurrence_grid_signup_post_invalid_occurrence(client_logged_in, event):
    url = reverse("occurrence_signup_grid", args=[event.id])
    response = client_logged_in.post(url, {"occurrence_id": 99999, "role": "opener"})

    # Should redirect without error
    assert response.status_code == 302
    assert response.url == reverse("occurrence_signup_grid", args=[event.id])


def test_occurrence_grid_signup_requires_login(client, event, future_occurrences):
    url = reverse("occurrence_signup_grid", args=[event.id])
    response = client.get(url)
    assert response.status_code == 302
    assert "/accounts/login/" in response.url
