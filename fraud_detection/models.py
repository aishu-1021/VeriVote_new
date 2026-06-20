from django.db import models


class FraudAlert(models.Model):

    ALERT_TYPE_CHOICES = [
        ('duplicate_vote', 'Duplicate Vote Attempt'),
        ('duplicate_aadhaar', 'Duplicate Aadhaar on Enrollment'),
        ('fingerprint_mismatch', 'Repeated Fingerprint Mismatch'),
        ('dead_voter', 'Deceased Voter Attempt'),
        ('cross_constituency', 'Cross-Constituency Vote Attempt'),
    ]

    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    alert_type = models.CharField(max_length=30, choices=ALERT_TYPE_CHOICES)
    voter_id = models.CharField(max_length=25)
    booth_id = models.CharField(max_length=20, blank=True)
    description = models.TextField()
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='medium')
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.severity.upper()}] {self.alert_type} — {self.voter_id}"