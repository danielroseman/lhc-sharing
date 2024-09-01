from direct_cloud_upload import CloudFileWidget, DdcuAdminMixin
from django.contrib import admin
from django import forms

from music.models import Song, DDCU_BUCKET_IDENTIFIER


class SongForm(forms.ModelForm):
    class Meta:
        model = Song
        fields = ['name', 'slug', 'created_at', 'current', 'files']

        widgets = {
            'files': CloudFileWidget(
                bucket_identifier=DDCU_BUCKET_IDENTIFIER,
                path_prefix="media/",
                include_timestamp=False,
                allow_multiple=True,
            )
        }

@admin.register(Song)
class SongAdmin(DdcuAdminMixin):
    list_display = ('name', 'current')
    list_editable = ['current']
    form = SongForm
    prepopulated_fields = {"slug": ["name"]}
