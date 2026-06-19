from django.db import models

class Voter(models.Model):
    voter_id = models.CharField(max_length=20, unique=True)
    full_name = models.CharField(max_length=100)
    fingerprint_template = models.BinaryField()
    has_voted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.voter_id} — {self.full_name}"