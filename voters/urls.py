from django.urls import path
from .views import (
    OfficerLoginView, OfficerLogoutView,
    DashboardStatsView,
    VoterEnrollView, VoterListView,
    CheckAadhaarView,
)

urlpatterns = [
    path('login/', OfficerLoginView.as_view()),
    path('logout/', OfficerLogoutView.as_view()),
    path('dashboard/', DashboardStatsView.as_view()),
    path('enroll/', VoterEnrollView.as_view()),
    path('list/', VoterListView.as_view()),
    path('check-aadhaar/', CheckAadhaarView.as_view()),
]