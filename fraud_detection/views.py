from rest_framework.views import APIView
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import FraudAlert

@method_decorator(csrf_exempt, name='dispatch')
class FraudAlertListView(APIView):
    def get(self, request):
        alerts = FraudAlert.objects.all().order_by('-created_at')[:50]
        data = [{
            'id': a.id,
            'alert_type': a.alert_type,
            'alert_type_display': a.get_alert_type_display(),
            'voter_id': a.voter_id,
            'booth_id': a.booth_id,
            'description': a.description,
            'severity': a.severity,
            'is_resolved': a.is_resolved,
            'created_at': a.created_at.strftime('%d %b %Y, %I:%M %p'),
        } for a in alerts]
        return Response(data)

    def patch(self, request, alert_id):
        try:
            alert = FraudAlert.objects.get(id=alert_id)
            alert.is_resolved = True
            alert.save()
            return Response({'message': 'Marked as resolved.'})
        except FraudAlert.DoesNotExist:
            return Response({'error': 'Alert not found.'}, status=404)