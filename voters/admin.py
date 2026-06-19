from django.contrib import admin
from .models import Voter

@admin.register(Voter)
class VoterAdmin(admin.ModelAdmin):
    list_display = ['voter_id', 'full_name', 'has_voted', 'created_at']
    search_fields = ['voter_id', 'full_name']
    list_filter = ['has_voted']