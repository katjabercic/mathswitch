from datetime import timedelta

from django.db import models
from django.utils import timezone


class SlurperRun(models.Model):
    """Tracks the last successful run of a named slurper for throttling."""

    source = models.CharField(max_length=8, unique=True)
    last_succeeded_at = models.DateTimeField()

    @classmethod
    def can_run(cls, source: str, min_interval: timedelta) -> bool:
        try:
            last = cls.objects.get(source=source).last_succeeded_at
        except cls.DoesNotExist:
            return True
        return timezone.now() - last >= min_interval

    @classmethod
    def mark_ran(cls, source: str) -> None:
        cls.objects.update_or_create(
            source=source,
            defaults={"last_succeeded_at": timezone.now()},
        )
