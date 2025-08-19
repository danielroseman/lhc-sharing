from dateutil import rrule
from django.db import models
from django.urls import reverse


# TODO: replace with hard-coded choice field?
class EventType(models.Model):
    label = models.CharField(max_length=100, unique=True, db_index=True)

    def __str__(self):
        return self.label


class Event(models.Model):
    title = models.CharField(max_length=255)
    description = models.CharField(
        max_length=255, blank=True, help_text="Internal description, not published"
    )
    event_type = models.ForeignKey(EventType, on_delete=models.CASCADE)
    details = models.TextField(blank=True)

    def __str__(self):
        return self.title

    def add_occurrences(self, start_time, end_time, location, **rrule_params):
        """
        Add one or more occurences to the event using a comparable API to
        ``dateutil.rrule``.

        If ``rrule_params`` does not contain a ``freq``, one will be defaulted
        to ``rrule.DAILY``.

        Because ``rrule.rrule`` returns an iterator that can essentially be
        unbounded, we need to slightly alter the expected behavior here in order
        to enforce a finite number of occurrence creation.

        If both ``count`` and ``until`` entries are missing from ``rrule_params``,
        only a single ``Occurrence`` instance will be created using the exact
        ``start_time`` and ``end_time`` values.

        Copied from django-swingtime.
        """
        count = rrule_params.get("count")
        until = rrule_params.get("until")
        if not (count or until):
            self.occurrence_set.create(start_time=start_time, end_time=end_time)
        else:
            rrule_params.setdefault("freq", rrule.DAILY)
            delta = end_time - start_time
            occurrences = []
            for ev in rrule.rrule(dtstart=start_time, **rrule_params):
                occurrences.append(
                    Occurrence(
                        start_time=ev,
                        end_time=ev + delta,
                        location=location,
                        event=self,
                    )
                )
            self.occurrence_set.bulk_create(occurrences)


class Occurrence(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    location = models.CharField(max_length=255, blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(blank=True, null=True)
    all_day = models.BooleanField(default=False)
    details = models.TextField(blank=True)

    class Meta:
        ordering = ["start_time"]

    @property
    def title(self):
        return self.event.title

    @property
    def event_type(self):
        return self.event.event_type

    @property
    def all_details(self):
        return "\n\n".join(
            filter(None, [self.event.details, self.location, self.details])
        )
