import hashlib
import json
from django.db import models
from django.utils import timezone


class Block(models.Model):
    index        = models.IntegerField()
    timestamp    = models.DateTimeField(default=timezone.now)
    event_type   = models.CharField(max_length=50)
    data         = models.JSONField()
    previous_hash = models.CharField(max_length=64)
    hash         = models.CharField(max_length=64, blank=True)

    def compute_hash(self):
        block_string = json.dumps({
            'index':         self.index,
            'timestamp':     self.timestamp.isoformat(),
            'event_type':    self.event_type,
            'data':          self.data,
            'previous_hash': self.previous_hash,
        }, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def save(self, *args, **kwargs):
        if not self.hash:
            self.hash = self.compute_hash()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Block #{self.index} | {self.event_type} | {self.hash[:12]}..."