from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Voter, EnrollmentOfficer
import base64


class EnrollmentOfficerSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnrollmentOfficer
        fields = ['badge_number', 'constituency']


class VoterListSerializer(serializers.ModelSerializer):
    """Lightweight — used for the dashboard table."""
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Voter
        fields = [
            'voter_id', 'full_name', 'assembly_constituency',
            'created_at', 'status', 'status_display'
        ]


class VoterDetailSerializer(serializers.ModelSerializer):
    """Full detail — used for enrollment form submission."""

    # Frontend sends raw Aadhaar → we hash it here, never store raw
    aadhaar_number = serializers.CharField(write_only=True, max_length=12)

    # Fingerprint comes as base64 string from the biometric engine
    fingerprint_b64 = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Voter
        fields = [
            'voter_id',
            'full_name', 'date_of_birth', 'gender',
            'relative_name', 'relation',
            'mobile_number', 'email',
            'house_number', 'street', 'city', 'pincode',
            'state', 'district', 'assembly_constituency',
            'parliamentary_constituency', 'assigned_booth',
            'aadhaar_number',       # write only — gets hashed
            'aadhaar_hash',         # read only — returned after save
            'passport_photo',
            'fingerprint_b64',      # write only — gets decoded to bytes
            'status', 'has_voted', 'created_at',
        ]
        read_only_fields = ['voter_id', 'aadhaar_hash', 'has_voted', 'created_at']

    def validate_aadhaar_number(self, value):
        value = value.replace(' ', '').replace('-', '')
        if not value.isdigit() or len(value) != 12:
            raise serializers.ValidationError("Aadhaar must be exactly 12 digits.")
        return value

    def validate_date_of_birth(self, value):
        from datetime import date
        today = date.today()
        age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
        if age < 18:
            raise serializers.ValidationError("Voter must be at least 18 years old.")
        return value

    def create(self, validated_data):
        raw_aadhaar = validated_data.pop('aadhaar_number')
        fingerprint_b64 = validated_data.pop('fingerprint_b64', None)

        # Hash Aadhaar
        aadhaar_hash = Voter.hash_aadhaar(raw_aadhaar)

        # Check duplicate Aadhaar
        if Voter.objects.filter(aadhaar_hash=aadhaar_hash).exists():
            raise serializers.ValidationError(
                {"aadhaar_number": "A voter with this Aadhaar is already enrolled."}
            )

        # Decode fingerprint from base64 to bytes
        fingerprint_bytes = None
        if fingerprint_b64:
            fingerprint_bytes = base64.b64decode(fingerprint_b64)

        voter = Voter.objects.create(
            aadhaar_hash=aadhaar_hash,
            fingerprint_template=fingerprint_bytes,
            **validated_data
        )
        return voter