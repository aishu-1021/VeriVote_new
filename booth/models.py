from django.db import models
from django.contrib.auth.models import User


class BoothOfficer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='booth_profile')
    badge_number = models.CharField(max_length=30, unique=True)
    booth_id = models.CharField(max_length=20)
    # e.g. "KA-04-007"
    constituency = models.CharField(max_length=100)
    is_session_active = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.badge_number} | Booth {self.booth_id}"


class VoteRecord(models.Model):
    """
    Created when a voter is verified at the booth.
    Intentionally does NOT store which candidate they voted for — secret ballot.
    """
    RESULT_CHOICES = [
        ('approved', 'Approved'),
        ('rejected_no_match', 'Rejected — Fingerprint No Match'),
        ('rejected_already_voted', 'Rejected — Already Voted'),
        ('rejected_not_enrolled', 'Rejected — Not Found'),
        ('fallback_otp', 'Approved via OTP Fallback'),
    ]

    voter_id = models.CharField(max_length=25)
    booth = models.ForeignKey(BoothOfficer, on_delete=models.SET_NULL, null=True)
    result = models.CharField(max_length=30, choices=RESULT_CHOICES)
    match_score = models.FloatField(null=True, blank=True)
    # The % score from your matcher.py — useful for audit
    timestamp = models.DateTimeField(auto_now_add=True)
    is_biometric_exempt = models.BooleanField(default=False)
    # True if OTP fallback was used

    def __str__(self):
        return f"{self.voter_id} | {self.result} @ {self.timestamp}"