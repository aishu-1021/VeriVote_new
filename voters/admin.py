from django.contrib import admin
from .models import Voter, EnrollmentOfficer

@admin.register(Voter)
class VoterAdmin(admin.ModelAdmin):
    list_display = ['voter_id', 'full_name', 'assembly_constituency', 'status', 'has_fingerprint', 'created_at']
    readonly_fields = ['voter_id', 'aadhaar_hash', 'has_fingerprint']

    def has_fingerprint(self, obj):
        if obj.fingerprint_template:
            return f'✅ Yes ({len(obj.fingerprint_template)} bytes)'
        return '❌ No'
    has_fingerprint.short_description = 'Fingerprint'

@admin.register(EnrollmentOfficer)
class EnrollmentOfficerAdmin(admin.ModelAdmin):
    list_display = ['badge_number', 'constituency', 'is_active_session']