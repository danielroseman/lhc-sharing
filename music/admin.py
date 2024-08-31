from direct_cloud_upload import CloudFileWidget, DdcuAdminMixin
from django.conf import settings
from django.contrib import admin
from django import forms
from google.cloud import storage

from music.models import Song, File, DDCU_BUCKET_IDENTIFIER


class FileForm(forms.ModelForm):
    class Meta:
        model = File
        fields = ['name', 'file']

        widgets = {
            'file': CloudFileWidget(
                bucket_identifier=DDCU_BUCKET_IDENTIFIER,
                path_prefix="media/",
                include_timestamp=False
            )
        }

class FileInline(admin.TabularInline):
    model = File
    form = FileForm



@admin.register(Song)
class SongAdmin(DdcuAdminMixin):
    inlines = [FileInline]
    list_display = ('name', 'current')
    list_editable = ['current']

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in formset.deleted_objects:
            obj.delete()
        for obj in instances:
            if obj.filetype == 'other':
                if obj.file:
                    if obj.file.endswith('.pdf'):
                        obj.filetype = 'pdf'
                    elif obj.file.endswith('mp3'):
                        obj.filetype = 'mp3'
            obj.save()
