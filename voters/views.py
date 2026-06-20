from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import authenticate
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import Voter, EnrollmentOfficer
from .serializers import VoterListSerializer, VoterDetailSerializer
import secrets

# Simple in-memory token store (fine for PBL demo)
active_tokens = {}

@method_decorator(csrf_exempt, name='dispatch')
class OfficerLoginView(APIView):
    def post(self, request):
        badge_number = request.data.get('badge_number', '').strip()
        password = request.data.get('password', '')

        try:
            officer = EnrollmentOfficer.objects.get(badge_number=badge_number)
        except EnrollmentOfficer.DoesNotExist:
            return Response({'error': 'Invalid badge number or password.'}, status=401)

        user = authenticate(request, username=officer.user.username, password=password)
        if user is None:
            return Response({'error': 'Invalid badge number or password.'}, status=401)

        # Generate a simple token
        token = secrets.token_hex(32)
        active_tokens[token] = user.id

        return Response({
            'token': token,
            'officer': {
                'name': f"{user.first_name} {user.last_name}",
                'badge_number': officer.badge_number,
                'constituency': officer.constituency,
            }
        })


@method_decorator(csrf_exempt, name='dispatch')
class OfficerLogoutView(APIView):
    def post(self, request):
        token = request.headers.get('Authorization', '').replace('Token ', '')
        if token in active_tokens:
            del active_tokens[token]
        return Response({'message': 'Logged out.'})


def get_user_from_token(request):
    """Helper — extracts user from token header."""
    from django.contrib.auth.models import User
    token = request.headers.get('Authorization', '').replace('Token ', '')
    user_id = active_tokens.get(token)
    if not user_id:
        return None
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None


@method_decorator(csrf_exempt, name='dispatch')
class DashboardStatsView(APIView):
    def get(self, request):
        user = get_user_from_token(request)
        if not user:
            return Response({'error': 'Not authenticated'}, status=401)

        try:
            officer = user.officer_profile
        except EnrollmentOfficer.DoesNotExist:
            return Response({'error': 'Not an enrollment officer'}, status=403)

        from django.utils import timezone
        from datetime import timedelta

        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())

        # Show ALL voters, not filtered by constituency
        base_qs = Voter.objects.all()
        today_enrollments = base_qs.filter(created_at__date=today)
        week_enrollments = base_qs.filter(created_at__date__gte=week_start)

        return Response({
            'officer_name': f"{user.first_name} {user.last_name}",
            'constituency': officer.constituency,
            'badge_number': officer.badge_number,
            'enrollments_today': today_enrollments.count(),
            'pending_today': today_enrollments.filter(status='pending').count(),
            'rejected_today': today_enrollments.filter(status='rejected').count(),
            'total_this_week': week_enrollments.count(),
            'recent_enrollments': VoterListSerializer(
                base_qs.order_by('-created_at')[:5], many=True
            ).data
        })


@method_decorator(csrf_exempt, name='dispatch')
class VoterEnrollView(APIView):
    def post(self, request):
        user = get_user_from_token(request)
        if not user:
            return Response({'error': 'Not authenticated'}, status=401)

        serializer = VoterDetailSerializer(data=request.data)
        if serializer.is_valid():
            try:
                officer = user.officer_profile
            except EnrollmentOfficer.DoesNotExist:
                officer = None

            voter = serializer.save(enrolled_by=officer, status='enrolled')
            return Response({
                'message': 'Voter enrolled successfully.',
                'voter_id': voter.voter_id
            }, status=201)

        return Response(serializer.errors, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class VoterListView(APIView):
    def get(self, request):
        user = get_user_from_token(request)
        if not user:
            return Response({'error': 'Not authenticated'}, status=401)

        voters = Voter.objects.all().order_by('-created_at')
        serializer = VoterListSerializer(voters, many=True)
        return Response(serializer.data)


@method_decorator(csrf_exempt, name='dispatch')
class CheckAadhaarView(APIView):
    def post(self, request):
        raw_aadhaar = request.data.get('aadhaar_number', '').replace(' ', '').replace('-', '')
        if not raw_aadhaar or len(raw_aadhaar) != 12:
            return Response({'error': 'Invalid Aadhaar'}, status=400)

        aadhaar_hash = Voter.hash_aadhaar(raw_aadhaar)
        exists = Voter.objects.filter(aadhaar_hash=aadhaar_hash).exists()
        return Response({'duplicate': exists})