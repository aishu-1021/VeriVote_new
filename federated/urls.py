from django.urls import path
from .views import RunFederatedView, FederatedResultsView

urlpatterns = [
    path('run/',     RunFederatedView.as_view()),
    path('results/', FederatedResultsView.as_view()),
]