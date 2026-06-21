from django.urls import path
from .views import ChainIntegrityView, ChainLogView

urlpatterns = [
    path('integrity/', ChainIntegrityView.as_view()),
    path('log/',       ChainLogView.as_view()),
]