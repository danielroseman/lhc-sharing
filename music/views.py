import datetime

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from swingtime.models import Occurrence
from swingtime.views import month_view

from music.models import Song


def home(request):
    occurrences = (
        Occurrence.objects.filter(start_time__gte=datetime.datetime.now())
        .select_related("event")
        .prefetch_related("notes")
        .order_by("start_time")
    )
    return render(request, "home.html", {"occurrences": occurrences})


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


@login_required
def month_view_notes(request, year, month):
    qs = Occurrence.objects.select_related("event").prefetch_related(
        "notes", "event__notes"
    )
    return month_view(request, year, month, queryset=qs)
