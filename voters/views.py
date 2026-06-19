from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Voter
import base64

@api_view(['POST'])
def enroll_voter(request):
    voter_id = request.data.get('voter_id')
    full_name = request.data.get('full_name')
    fingerprint_template = request.data.get('fingerprint_template')

    if not all([voter_id, full_name, fingerprint_template]):
        return Response(
            {'error': 'voter_id, full_name and fingerprint_template are required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if Voter.objects.filter(voter_id=voter_id).exists():
        return Response(
            {'error': f'Voter {voter_id} already enrolled'},
            status=status.HTTP_409_CONFLICT
        )

    template_bytes = base64.b64decode(fingerprint_template)
    Voter.objects.create(
        voter_id=voter_id,
        full_name=full_name,
        fingerprint_template=template_bytes
    )

    return Response(
        {'success': True, 'message': f'Voter {voter_id} enrolled successfully'},
        status=status.HTTP_201_CREATED
    )


@api_view(['GET'])
def get_voter(request, voter_id):
    try:
        voter = Voter.objects.get(voter_id=voter_id)
    except Voter.DoesNotExist:
        return Response(
            {'error': f'Voter {voter_id} not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    template_b64 = base64.b64encode(bytes(voter.fingerprint_template)).decode('utf-8')

    return Response({
        'voter_id': voter.voter_id,
        'full_name': voter.full_name,
        'has_voted': voter.has_voted,
        'fingerprint_template': template_b64
    })


@api_view(['POST'])
def record_vote(request):
    voter_id = request.data.get('voter_id')

    if not voter_id:
        return Response(
            {'error': 'voter_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        voter = Voter.objects.get(voter_id=voter_id)
    except Voter.DoesNotExist:
        return Response(
            {'error': f'Voter {voter_id} not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    if voter.has_voted:
        return Response(
            {'error': f'Voter {voter_id} has already voted'},
            status=status.HTTP_409_CONFLICT
        )

    voter.has_voted = True
    voter.save()

    return Response(
        {'success': True, 'message': f'Vote recorded for {voter_id}'}
    )