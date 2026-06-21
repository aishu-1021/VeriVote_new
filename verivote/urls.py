from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/',          admin.site.urls),
    path('api/',            include('voters.urls')),
    path('api/booth/',      include('booth.urls')),
    path('api/fraud/',      include('fraud_detection.urls')),
    path('api/chain/',      include('audit_chain.urls')),
    path('api/federated/',  include('federated.urls')),
]