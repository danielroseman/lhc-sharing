from datetime import timedelta
import json
import pathlib

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
    slug = models.SlugField()
    created_at = models.DateTimeField(default=timezone.now)
    current = models.BooleanField(default=True, help_text="Show in list of current songs")
    files = models.TextField(blank=True)

    def __str__(self):
        return self.name

    @property
    def file_urls(self):
        file_list = json.loads(self.files)
        files = []
        for file in file_list:
            blob = gcs_bucket.blob(file)
            signed_url = blob.generate_signed_url(response_disposition="attachment",
                                                  expiration=timedelta(seconds=86400))
            path = pathlib.Path(file)
            files.append({"url": signed_url, "path": path})
        return files
