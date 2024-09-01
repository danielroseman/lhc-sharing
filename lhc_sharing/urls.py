"""
URL configuration for lhc_sharing project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

import direct_cloud_upload

from music import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path("invitations/", include('invitations.urls', namespace='invitations')),
    path('accounts/', include('allauth.urls')),
    path('direct_cloud_upload/', include(direct_cloud_upload.urlpatterns)),
    path('', views.home, name='home'),
    path('songs', views.CurrentMusicList.as_view(), name='songs'),
    path('all-songs', views.MusicList.as_view(), name='all_songs'),
    path('song/<str:slug>', views.MusicDetail.as_view(), name='song_detail'),
]
