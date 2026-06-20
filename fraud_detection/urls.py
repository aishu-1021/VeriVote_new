from django.urls import path
from .views import FraudAlertListView
urlpatterns = [
    path('alerts/', FraudAlertListView.as_view()),
    path('alerts/<int:alert_id>/resolve/', FraudAlertListView.as_view()),
]