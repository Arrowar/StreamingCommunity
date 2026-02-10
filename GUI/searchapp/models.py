from django.db import models
from django.utils import timezone


class WatchlistItem(models.Model):
    name = models.CharField(max_length=255)
    source_alias = models.CharField(max_length=100)
    item_payload = models.TextField()
    poster_url = models.URLField(max_length=500, null=True, blank=True)
    num_seasons = models.IntegerField(default=0)
    last_season_episodes = models.IntegerField(default=0)
    
    # Metadata for tracking changes
    added_at = models.DateTimeField(default=timezone.now)
    last_checked_at = models.DateTimeField(default=timezone.now)
    
    # Flags to indicate new content
    has_new_seasons = models.BooleanField(default=False)
    has_new_episodes = models.BooleanField(default=False)

    class Meta:
        ordering = ['-added_at']
        unique_together = ('name', 'source_alias')

    def __str__(self):
        return f"{self.name} ({self.source_alias})"