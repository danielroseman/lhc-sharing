from django.contrib import admin

from music.models import Song, File


class FileInline(admin.TabularInline):
    model = File



@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    inlines = [FileInline]
    list_display = ('name', 'current')

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in formset.deleted_objects:
            obj.delete()
        for obj in instances:
            if obj.filetype == 'other':
                if obj.file:
                    if obj.file.url.endswith('.pdf'):
                        obj.filetype = 'pdf'
                    elif obj.file.url.endswith('mp3'):
                        obj.filetype = 'mp3'
            obj.save()
