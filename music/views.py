from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView

from music.models import Song, File

# Create your views here.
def home(request):
    return render(request, 'home.html')


#  @login_required
#  def current_music(request):

class CurrentMusicList(LoginRequiredMixin, ListView):
    extra_context = {"current": True}
    queryset = Song.objects.filter(current=True).order_by('name')
    template_name = 'songs.html'


class MusicList(LoginRequiredMixin, ListView):
    extra_context = {"current": False}
    queryset = Song.objects.all().order_by('name')
    template_name = 'songs.html'


class MusicDetail(LoginRequiredMixin, DetailView):
    template_name = 'files.html'
    model = Song
