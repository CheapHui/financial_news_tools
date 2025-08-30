from django.db import models

class JobRun(models.Model):
    name = models.CharField(max_length=80)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    success = models.BooleanField(default=False)
    processed = models.IntegerField(default=0)
    duration_ms = models.IntegerField(default=0)
    error = models.TextField(blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=["name", "started_at"]),
            models.Index(fields=["started_at"]),
        ]

    def __str__(self):
        s = "OK" if self.success else "ERR"
        return f"{self.name} {s} {self.started_at.isoformat()} ({self.processed})"