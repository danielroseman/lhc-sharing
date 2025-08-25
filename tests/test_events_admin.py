import datetime
from unittest import mock

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.utils import timezone

from events.admin import EventAdmin, RecurringEventForm
from events.models import Event, EventType, Occurrence


@pytest.fixture(autouse=True)
def tz():
    timezone.activate(datetime.timezone.utc)


@pytest.fixture
def user(db):
    return User.objects.create_superuser(
        username="admin", password="pass", email="admin@test.com"
    )


@pytest.fixture
def event_type(db):
    return EventType.objects.create(label="Test Type")


@pytest.fixture
def event(db, event_type):
    return Event.objects.create(
        title="Test Event", description="Test Description", event_type=event_type
    )


@pytest.fixture
def admin_site():
    return AdminSite()


@pytest.fixture
def event_admin(admin_site):
    return EventAdmin(Event, admin_site)


class TestRecurringEventForm:
    def test_form_valid_with_all_required_fields(self, event_type):
        form_data = {
            "title": "Test Event",
            "description": "Test Description",
            "event_type": event_type.id,
            "start_time_0": "2025-09-01",
            "start_time_1": "10:00:00",
            "end_time": "12:00",
            "days": [1, 3, 5],  # Monday, Wednesday, Friday
            "count": 5,
        }
        form = RecurringEventForm(data=form_data)
        assert form.is_valid(), form.errors

        # Check that end datetime is properly constructed
        cleaned_data = form.cleaned_data
        expected_end = datetime.datetime(
            2025, 9, 1, 12, 0, tzinfo=datetime.timezone.utc
        )
        assert cleaned_data["end"] == expected_end

    def test_form_valid_with_until_date(self, event_type):
        form_data = {
            "title": "Test Event",
            "description": "Test Description",
            "event_type": event_type.id,
            "start_time_0": "2025-09-01",
            "start_time_1": "10:00:00",
            "end_time": "12:00",
            "days": [2, 4],  # Tuesday, Thursday
            "until": datetime.date(2025, 12, 31),
        }
        form = RecurringEventForm(data=form_data)
        assert form.is_valid()

        # Check that until datetime is properly constructed
        cleaned_data = form.cleaned_data
        expected_until = datetime.datetime(
            2025, 12, 31, 12, 0, tzinfo=datetime.timezone.utc
        )
        assert cleaned_data["until"] == expected_until

    def test_form_invalid_missing_start_time(self, event_type):
        form_data = {
            "title": "Test Event",
            "event_type": event_type.id,
            "end_time": "12:00",
            "days": [1, 3, 5],
            "count": 5,
        }
        form = RecurringEventForm(data=form_data)
        assert not form.is_valid()
        assert (
            "To create recurring events you must specify" in form.errors["__all__"][0]
        )

    def test_form_invalid_missing_end_time(self, event_type):
        form_data = {
            "title": "Test Event",
            "event_type": event_type.id,
            "start_time_0": "2025-09-01",
            "start_time_1": "10:00:00",
            "days": [1, 3, 5],
            "count": 5,
        }
        form = RecurringEventForm(data=form_data)
        assert not form.is_valid()
        assert (
            "To create recurring events you must specify" in form.errors["__all__"][0]
        )

    def test_form_invalid_missing_days(self, event_type):
        form_data = {
            "title": "Test Event",
            "event_type": event_type.id,
            "start_time_0": "2025-09-01",
            "start_time_1": "10:00:00",
            "end_time": "12:00",
            "count": 5,
        }
        form = RecurringEventForm(data=form_data)
        assert not form.is_valid()
        assert (
            "To create recurring events you must specify" in form.errors["__all__"][0]
        )

    def test_form_invalid_missing_count_and_until(self, event_type):
        form_data = {
            "title": "Test Event",
            "event_type": event_type.id,
            "start_time_0": "2025-09-01",
            "start_time_1": "10:00:00",
            "end_time": "12:00",
            "days": [1, 3, 5],
        }
        form = RecurringEventForm(data=form_data)
        assert not form.is_valid()
        assert (
            "To create recurring events you must specify" in form.errors["__all__"][0]
        )

    def test_form_invalid_both_count_and_until(self, event_type):
        form_data = {
            "title": "Test Event",
            "event_type": event_type.id,
            "start_time_0": "2025-09-01",
            "start_time_1": "10:00:00",
            "end_time": "12:00",
            "days": [1, 3, 5],
            "count": 5,
            "until": datetime.date(2025, 12, 31),
        }
        form = RecurringEventForm(data=form_data)
        assert not form.is_valid()
        assert (
            "You can't specify both a count and an end date"
            in form.errors["__all__"][0]
        )

    def test_form_valid_without_recurring_fields(self, event_type):
        # Form should be valid if no recurring fields are provided at all
        form_data = {
            "title": "Test Event",
            "description": "Test Description",
            "event_type": event_type.id,
        }
        form = RecurringEventForm(data=form_data)
        assert form.is_valid()


class TestEventAdmin:
    def test_get_fieldsets_collapses_recurring_when_occurrences_exist(
        self, event_admin, event, user
    ):
        # Create an occurrence for the event
        Occurrence.objects.create(
            event=event,
            start_time=timezone.now(),
            end_time=timezone.now() + datetime.timedelta(hours=2),
        )

        request = mock.Mock()
        request.user = user

        fieldsets = event_admin.get_fieldsets(request, event)

        # The second fieldset should have collapse class
        assert "collapse" in fieldsets[1][1]["classes"]

    def test_get_fieldsets_no_collapse_when_no_occurrences(
        self, event_admin, event, user
    ):
        request = mock.Mock()
        request.user = user

        fieldsets = event_admin.get_fieldsets(request, event)

        # The second fieldset should not have classes or should not include collapse
        classes = fieldsets[1][1].get("classes", [])
        assert "collapse" not in classes

    def test_save_model_creates_occurrences_when_recurring_data_provided(
        self, event_admin, event_type, user
    ):
        request = mock.Mock()
        request.user = user

        # Create form with recurring data
        form_data = {
            "title": "Recurring Event",
            "description": "Test Description",
            "event_type": event_type.id,
            "start_time_0": "2025-09-01",
            "start_time_1": "10:00:00",
            "end_time": "12:00",
            "days": [1, 3, 5],  # Monday, Wednesday, Friday
            "count": 3,
            "location": "Test Location",
        }

        form = RecurringEventForm(data=form_data)
        assert form.is_valid()

        # Create event instance
        event = Event(
            title="Recurring Event",
            description="Test Description",
            event_type=event_type,
        )

        # Mock the add_occurrences method to verify it's called
        with mock.patch.object(event, "add_occurrences") as mock_add:
            event_admin.save_model(request, event, form, change=False)

            # Verify add_occurrences was called with correct parameters
            mock_add.assert_called_once()
            call_args = mock_add.call_args[1]
            assert call_args["start_time"] == form.cleaned_data["start_time"]
            assert call_args["end_time"] == form.cleaned_data["end"]
            assert call_args["count"] == 3
            assert call_args["location"] == "Test Location"
            assert len(call_args["byweekday"]) == 3  # Monday, Wednesday, Friday

    def test_save_model_no_occurrences_when_no_recurring_data(
        self, event_admin, event_type, user
    ):
        request = mock.Mock()
        request.user = user

        # Create form without recurring data
        form_data = {
            "title": "Simple Event",
            "description": "Test Description",
            "event_type": event_type.id,
        }

        form = RecurringEventForm(data=form_data)
        assert form.is_valid()

        # Create event instance
        event = Event(
            title="Simple Event", description="Test Description", event_type=event_type
        )

        # Mock the add_occurrences method to verify it's not called
        with mock.patch.object(event, "add_occurrences") as mock_add:
            event_admin.save_model(request, event, form, change=False)

            # Verify add_occurrences was not called
            mock_add.assert_not_called()
