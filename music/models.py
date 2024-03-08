from django.db import models
from django.utils import timezone


class Song(models.Model):
    name = models.CharField(max_length=255, blank=False, unique=True, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)
    current = models.BooleanField(default=True, help_text="Show in list of current songs")

    def __str__(self):
        return self.name


class File(models.Model):
    name = models.CharField(max_length=255, blank=False)
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    file = models.FileField()

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"{self.name} ({self.song.name})"

    def filetype(self):
        if self.file.url.endswith('pdf'):
            return 'pdf'
        elif self.file.url.endswith('mp3'):
            return 'mp3'
        else:
            return 'other'
