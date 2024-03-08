from django.contrib import admin

from music.models import Song, File


class FileInline(admin.TabularInline):
    model = File


@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    inlines = [FileInline]
    list_display = ('name', 'current')

