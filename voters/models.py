import hashlib
from django.db import models
from django.contrib.auth.models import User


class EnrollmentOfficer(models.Model):
    """
    Wraps Django's built-in User model with ECI-specific fields.
    Django User already handles username (officer ID), password, login.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='officer_profile')
    badge_number = models.CharField(max_length=30, unique=True)
    # e.g. "ECI/KA/OFF/2024/0042"
    constituency = models.CharField(max_length=100)
    is_active_session = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.badge_number} — {self.constituency}"


class Voter(models.Model):

    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Transgender / Other'),
    ]

    RELATION_CHOICES = [
        ('father', 'Father'),
        ('husband', 'Husband'),
        ('mother', 'Mother'),
        ('guardian', 'Guardian'),
    ]

    STATUS_CHOICES = [
        ('enrolled', 'Enrolled'),
        ('pending', 'Pending'),
        ('rejected', 'Rejected'),
        ('deceased', 'Deceased'),
        ('migrated', 'Migrated'),
    ]

    # ── Auto-generated ─────────────────────────────────────────────────────
    voter_id = models.CharField(max_length=25, unique=True, blank=True)
    # Generated as KA/04/2025/XXXXXX — see save() below

    # ── Step 1: Personal Details ────────────────────────────────────────────
    full_name = models.CharField(max_length=150)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    relative_name = models.CharField(max_length=150)
    relation = models.CharField(max_length=10, choices=RELATION_CHOICES)
    mobile_number = models.CharField(max_length=15)
    email = models.EmailField(blank=True, null=True)

    # ── Step 2: Address & Constituency ─────────────────────────────────────
    house_number = models.CharField(max_length=150)
    street = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    pincode = models.CharField(max_length=6)
    state = models.CharField(max_length=100, default='Karnataka')
    district = models.CharField(max_length=100)
    assembly_constituency = models.CharField(max_length=150)
    parliamentary_constituency = models.CharField(max_length=150, blank=True)
    assigned_booth = models.CharField(max_length=100, blank=True)

    # ── Step 3: Documents & Biometrics ─────────────────────────────────────
    aadhaar_hash = models.CharField(max_length=64, unique=True)
    # SHA-256 of raw Aadhaar — stored as hex string (64 chars)
    # Raw Aadhaar number is NEVER stored

    passport_photo = models.ImageField(upload_to='voter_photos/', null=True, blank=True)

    fingerprint_template = models.BinaryField(null=True, blank=True)
    # Serialized ORB descriptor from your extractor.py (pickle bytes)

    # ── Status & Audit ──────────────────────────────────────────────────────
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    has_voted = models.BooleanField(default=False)
    enrolled_by = models.ForeignKey(
        EnrollmentOfficer,
        on_delete=models.SET_NULL,
        null=True,
        related_name='enrollments'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.voter_id:
            from django.utils import timezone
            year = timezone.now().year
            # Count ALL voters to get next number (not just by constituency)
            count = Voter.objects.count() + 1
            self.voter_id = f"KA/04/{year}/{count:06d}"
        super().save(*args, **kwargs)

    @staticmethod
    def hash_aadhaar(raw_aadhaar: str) -> str:
        """Call this before saving — never pass raw Aadhaar to the model."""
        return hashlib.sha256(raw_aadhaar.strip().encode()).hexdigest()

    def __str__(self):
        return f"{self.voter_id} — {self.full_name}"