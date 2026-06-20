from django.urls import path, re_path
from .views import (
    CaptureFingerprintView,
    BoothOfficerLoginView,
    BoothOfficerLogoutView,
    BoothDashboardView,
    VoterLookupView,
    VerifyFingerprintView,
    RecordVoteView,
)

urlpatterns = [
    path('capture-fingerprint/', CaptureFingerprintView.as_view()),
    path('login/', BoothOfficerLoginView.as_view()),
    path('logout/', BoothOfficerLogoutView.as_view()),
    path('dashboard/', BoothDashboardView.as_view()),
    re_path(r'^voter/(?P<voter_id>.+)/$', VoterLookupView.as_view()),
    path('verify-fingerprint/', VerifyFingerprintView.as_view()),
    path('record-vote/', RecordVoteView.as_view()),
]