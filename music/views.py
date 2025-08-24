from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.utils import timezone
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView

from events.models import Occurrence
from music.models import Song


def home(request):
    occurrences = (
        Occurrence.objects.filter(start_time__gte=timezone.now())
        .select_related("event")
        .order_by("start_time")
    )
    next_rehearsal = occurrences.filter(event__event_type__label="Rehearsal").first()
    upcoming_performances = occurrences.filter(event__event_type__label="Performance")
    return render(
        request,
        "home.html",
        {
            "next_rehearsal": next_rehearsal,
            "upcoming_performances": upcoming_performances,
        },
    )


class CurrentMusicList(LoginRequiredMixin, ListView):
    extra_context = {"current": True}
    queryset = Song.objects.filter(current=True).order_by("name")
    template_name = "songs.html"


class MusicList(LoginRequiredMixin, ListView):
    extra_context = {"current": False}
    queryset = Song.objects.all().order_by("name")
    template_name = "songs.html"


class MusicDetail(LoginRequiredMixin, DetailView):
    template_name = "files.html"
    model = Song
