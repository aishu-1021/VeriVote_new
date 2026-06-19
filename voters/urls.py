from django.urls import path
from . import views

urlpatterns = [
    path('enroll-voter/', views.enroll_voter),
    path('voter/<str:voter_id>/', views.get_voter),
    path('record-vote/', views.record_vote),
]