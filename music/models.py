from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from direct_cloud_upload import register_gcs_bucket
from google.cloud import storage

client = storage.Client(credentials=settings.GS_CREDENTIALS)
gcs_bucket = client.bucket('london-humanist-choir')
DDCU_BUCKET_IDENTIFIER = register_gcs_bucket(gcs_bucket)

class Song(models.Model):
    name = models.CharField(max_length=255, blank=False, unique=True, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)
    current = models.BooleanField(default=True, help_text="Show in list of current songs")

    def __str__(self):
        return self.name


class File(models.Model):
    class FileTypes(models.TextChoices):
        PDF = "pdf"
        MP3 = "mp3"
        OTHER = "other"

    name = models.CharField(max_length=255, blank=False)
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    file = models.TextField()
    filetype = models.CharField(max_length=35, choices=FileTypes.choices, default="other")

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"{self.name} ({self.song.name})"

    @property
    def file_url(self):
        blob = gcs_bucket.blob(self.file)
        return blob.generate_signed_url(expiration=timedelta(seconds=86400))

