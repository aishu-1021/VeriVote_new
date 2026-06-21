from rest_framework.views import APIView
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .chain import verify_chain
from .models import Block


@method_decorator(csrf_exempt, name='dispatch')
class ChainIntegrityView(APIView):
    def get(self, request):
        result = verify_chain()
        return Response(result)


@method_decorator(csrf_exempt, name='dispatch')
class ChainLogView(APIView):
    """Returns last 50 blocks for the admin dashboard."""
    def get(self, request):
        blocks = Block.objects.order_by('-index')[:50]
        data = [{
            'index':         b.index,
            'event_type':    b.event_type,
            'data':          b.data,
            'hash':          b.hash,
            'previous_hash': b.previous_hash,
            'timestamp':     b.timestamp.strftime('%d %b %Y, %I:%M %p'),
        } for b in blocks]
        return Response(data)