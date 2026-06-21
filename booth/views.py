import sys
import os
import base64
import hashlib
import pickle
import secrets
import cv2
from rest_framework.views import APIView
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from .models import BoothOfficer, VoteRecord
from voters.models import Voter
from fraud_detection.models import FraudAlert
from audit_chain.chain import append_block

BIOMETRIC_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'biometric'
)
if BIOMETRIC_PATH not in sys.path:
    sys.path.insert(0, BIOMETRIC_PATH)

booth_tokens = {}


def hash_voter_id(voter_id: str) -> str:
    """Hash voter ID before storing on blockchain — never store raw IDs on-chain."""
    return hashlib.sha256(voter_id.encode()).hexdigest()[:16]


def get_booth_user(request):
    token = request.headers.get('Authorization', '').replace('Token ', '')
    user_id = booth_tokens.get(token)
    if not user_id:
        return None
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None


# ──────────────────────────────────────────────
# ISO MATCHING — Primary method using MFS100 SDK
# ──────────────────────────────────────────────

def iso_match_with_scanner(live_iso_bytes, stored_iso_bytes):
    """
    Uses MFS100 MatchISO for proper minutiae-based matching.
    Returns (is_match, score) on success.
    Returns (None, None) if scanner is unavailable — caller handles fallback.
    Score 0-100. Threshold: 40.
    """
    try:
        import clr
        DLL_PATH = r"C:\Program Files\Mantra\MFS100\Driver\MFS100Test\MANTRA.MFS100.dll"
        DLL_FOLDER = os.path.dirname(DLL_PATH)
        if DLL_FOLDER not in sys.path:
            sys.path.append(DLL_FOLDER)
        clr.AddReference(DLL_PATH)
        from MANTRA import MFS100
        import System

        mfs = MFS100()

        if not mfs.IsConnected():
            raise Exception("Scanner not connected")

        result = mfs.Init()
        code = result[0] if isinstance(result, tuple) else result
        if int(code) != 0:
            raise Exception(f"Init() failed with code: {code}")

        t1 = System.Array[System.Byte](list(live_iso_bytes))
        t2 = System.Array[System.Byte](list(stored_iso_bytes))
        raw = mfs.MatchISO(t1, t2, System.Int32(0))

        if isinstance(raw, tuple):
            error_code = int(raw[0])
            score = int(raw[1]) if len(raw) > 1 else 0
        else:
            error_code = 0
            score = int(raw)

        try:
            mfs.Uninit()
        except Exception:
            pass

        if error_code != 0:
            raise Exception(f"MatchISO returned error code: {error_code}")

        is_match = score >= 40
        print(f"[ISO Match] Score: {score}/100, Threshold: 40, Match: {is_match}")
        return is_match, float(score)

    except Exception as e:
        print(f"[ISO] Matching failed — scanner unavailable: {e}")
        return None, None


@method_decorator(csrf_exempt, name='dispatch')
class BoothOfficerLoginView(APIView):
    def post(self, request):
        badge_number = request.data.get('badge_number', '').strip()
        password = request.data.get('password', '')

        try:
            officer = BoothOfficer.objects.get(badge_number=badge_number)
        except BoothOfficer.DoesNotExist:
            return Response({'error': 'Invalid badge number or password.'}, status=401)

        user = authenticate(request, username=officer.user.username, password=password)
        if user is None:
            return Response({'error': 'Invalid badge number or password.'}, status=401)

        token = secrets.token_hex(32)
        booth_tokens[token] = user.id
        officer.is_session_active = True
        officer.save()

        append_block(
            event_type='OFFICER_LOGIN',
            data={
                'badge_number': officer.badge_number,
                'booth_id':     officer.booth_id,
                'constituency': officer.constituency,
            }
        )

        return Response({
            'token': token,
            'officer': {
                'name': f"{user.first_name} {user.last_name}",
                'badge_number': officer.badge_number,
                'booth_id': officer.booth_id,
                'constituency': officer.constituency,
            }
        })


@method_decorator(csrf_exempt, name='dispatch')
class BoothOfficerLogoutView(APIView):
    def post(self, request):
        token = request.headers.get('Authorization', '').replace('Token ', '')
        user = get_booth_user(request)

        if user:
            try:
                officer = user.booth_profile
                append_block(
                    event_type='OFFICER_LOGOUT',
                    data={
                        'badge_number': officer.badge_number,
                        'booth_id':     officer.booth_id,
                    }
                )
            except Exception:
                pass

        if token in booth_tokens:
            del booth_tokens[token]

        return Response({'message': 'Logged out.'})


@method_decorator(csrf_exempt, name='dispatch')
class BoothDashboardView(APIView):
    def get(self, request):
        user = get_booth_user(request)
        if not user:
            return Response({'error': 'Not authenticated'}, status=401)

        try:
            officer = user.booth_profile
        except BoothOfficer.DoesNotExist:
            return Response({'error': 'Not a booth officer'}, status=403)

        from django.utils import timezone
        today = timezone.now().date()

        today_records = VoteRecord.objects.filter(booth=officer, timestamp__date=today)
        total_registered = Voter.objects.filter(assembly_constituency=officer.constituency).count()
        votes_cast = today_records.filter(result='approved').count()
        rejected_today = today_records.exclude(result='approved').count()
        remaining = max(0, total_registered - votes_cast)

        recent = today_records.order_by('-timestamp')[:5]
        recent_data = [{
            'voter_id':            r.voter_id,
            'result':              r.result,
            'timestamp':           r.timestamp.strftime('%I:%M %p'),
            'match_score':         r.match_score,
            'is_biometric_exempt': r.is_biometric_exempt,
        } for r in recent]

        return Response({
            'officer_name':     f"{user.first_name} {user.last_name}",
            'badge_number':     officer.badge_number,
            'booth_id':         officer.booth_id,
            'constituency':     officer.constituency,
            'total_registered': total_registered,
            'votes_cast':       votes_cast,
            'rejected_today':   rejected_today,
            'remaining':        remaining,
            'recent_activity':  recent_data,
        })


@method_decorator(csrf_exempt, name='dispatch')
class VoterLookupView(APIView):
    def get(self, request, voter_id):
        user = get_booth_user(request)
        if not user:
            return Response({'error': 'Not authenticated'}, status=401)

        try:
            voter = Voter.objects.get(voter_id=voter_id.upper())
            return Response({
                'voter_id':              voter.voter_id,
                'full_name':             voter.full_name,
                'assembly_constituency': voter.assembly_constituency,
                'assigned_booth':        voter.assigned_booth,
                'has_voted':             voter.has_voted,
                'status':                voter.status,
                'fingerprint_template':  base64.b64encode(
                    bytes(voter.fingerprint_template)
                ).decode('utf-8') if voter.fingerprint_template else None,
            })
        except Voter.DoesNotExist:
            return Response({'error': 'Voter not found.'}, status=404)


@method_decorator(csrf_exempt, name='dispatch')
class VerifyFingerprintView(APIView):
    def post(self, request):
        user = get_booth_user(request)
        if not user:
            return Response({'error': 'Not authenticated'}, status=401)

        voter_id = request.data.get('voter_id', '').strip().upper()
        stored_template_b64 = request.data.get('stored_template_b64', '')

        if not voter_id or not stored_template_b64:
            return Response({'error': 'voter_id and stored_template_b64 required.'}, status=400)

        try:
            officer = user.booth_profile
        except BoothOfficer.DoesNotExist:
            return Response({'error': 'Not a booth officer'}, status=403)

        try:
            from capture import capture_and_save

            safe_id = voter_id.replace('/', '_').replace('\\', '_')
            capture_result = capture_and_save(voter_id=f"verify_{safe_id}")

            if capture_result is None:
                append_block(
                    event_type='VERIFICATION_FAILED',
                    data={
                        'voter_id_hash': hash_voter_id(voter_id),
                        'booth_id':      officer.booth_id,
                        'reason':        'Fingerprint scan failed after 3 attempts.',
                    }
                )
                return Response({
                    'result': 'REJECTED',
                    'reason': 'Fingerprint scan failed after 3 attempts.',
                    'match_score': 0,
                })

            live_iso_bytes = capture_result.get('iso_template')

            if not live_iso_bytes:
                return Response({
                    'result': 'REJECTED',
                    'reason': 'ISO template not returned by scanner.',
                    'match_score': 0,
                })

            stored_iso_bytes = base64.b64decode(stored_template_b64)
            is_match, score = iso_match_with_scanner(live_iso_bytes, stored_iso_bytes)

            if is_match is None:
                append_block(
                    event_type='VERIFICATION_FAILED',
                    data={
                        'voter_id_hash': hash_voter_id(voter_id),
                        'booth_id':      officer.booth_id,
                        'reason':        'Scanner unavailable.',
                    }
                )
                return Response({
                    'result': 'REJECTED',
                    'reason': 'Biometric scanner unavailable. Please use OTP fallback.',
                    'match_score': 0,
                })

            if is_match:
                append_block(
                    event_type='VERIFICATION_APPROVED',
                    data={
                        'voter_id_hash': hash_voter_id(voter_id),
                        'booth_id':      officer.booth_id,
                        'officer_id':    officer.badge_number,
                        'match_score':   score,
                    }
                )
                return Response({
                    'result': 'APPROVED',
                    'reason': 'Fingerprint matched successfully.',
                    'match_score': score,
                })
            else:
                FraudAlert.objects.create(
                    alert_type='fingerprint_mismatch',
                    voter_id=voter_id,
                    booth_id=officer.booth_id,
                    description=f'Fingerprint mismatch at booth {officer.booth_id}. ISO Score: {score}',
                    severity='high',
                )
                append_block(
                    event_type='VERIFICATION_REJECTED',
                    data={
                        'voter_id_hash': hash_voter_id(voter_id),
                        'booth_id':      officer.booth_id,
                        'officer_id':    officer.badge_number,
                        'match_score':   score,
                        'reason':        'Fingerprint mismatch.',
                    }
                )
                return Response({
                    'result': 'REJECTED',
                    'reason': 'Fingerprint does not match enrolled data.',
                    'match_score': score,
                })

        except Exception as e:
            print(f"[ERROR] VerifyFingerprintView: {e}")
            return Response({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class RecordVoteView(APIView):
    def post(self, request):
        user = get_booth_user(request)
        if not user:
            return Response({'error': 'Not authenticated'}, status=401)

        voter_id = request.data.get('voter_id', '').strip().upper()
        match_score = request.data.get('match_score', 0)

        try:
            officer = user.booth_profile
        except BoothOfficer.DoesNotExist:
            return Response({'error': 'Not a booth officer'}, status=403)

        try:
            voter = Voter.objects.get(voter_id=voter_id)
        except Voter.DoesNotExist:
            return Response({'error': 'Voter not found.'}, status=404)

        if voter.has_voted:
            FraudAlert.objects.create(
                alert_type='duplicate_vote',
                voter_id=voter_id,
                booth_id=officer.booth_id,
                description=f'Duplicate vote attempt at booth {officer.booth_id}.',
                severity='high',
            )
            append_block(
                event_type='DUPLICATE_VOTE_ATTEMPT',
                data={
                    'voter_id_hash': hash_voter_id(voter_id),
                    'booth_id':      officer.booth_id,
                    'officer_id':    officer.badge_number,
                }
            )
            return Response({'error': 'Voter has already voted.'}, status=400)

        voter.has_voted = True
        voter.save()

        VoteRecord.objects.create(
            voter_id=voter_id,
            booth=officer,
            result='approved',
            match_score=match_score,
        )

        append_block(
            event_type='VOTE_RECORDED',
            data={
                'voter_id_hash': hash_voter_id(voter_id),
                'booth_id':      officer.booth_id,
                'officer_id':    officer.badge_number,
                'match_score':   float(match_score),
            }
        )

        return Response({'message': 'Vote recorded successfully.'})


@method_decorator(csrf_exempt, name='dispatch')
class CaptureFingerprintView(APIView):
    def post(self, request):
        try:
            from capture import capture_and_save

            capture_result = capture_and_save(voter_id="live_scan")
            if capture_result is None:
                return Response({
                    'error': 'Fingerprint capture failed. Check scanner connection.'
                }, status=400)

            iso_bytes = capture_result.get('iso_template')
            quality = capture_result.get('quality', 0)

            if not iso_bytes:
                return Response({'error': 'ISO template not returned by scanner.'}, status=400)

            iso_b64 = base64.b64encode(iso_bytes).decode('utf-8')

            return Response({
                'success':        True,
                'descriptor_b64': iso_b64,
                'quality':        quality,
                'keypoint_count': len(iso_bytes)
            })

        except ImportError as e:
            return Response({'error': f'Biometric engine import failed: {str(e)}'}, status=500)
        except Exception as e:
            return Response({'error': str(e)}, status=500)