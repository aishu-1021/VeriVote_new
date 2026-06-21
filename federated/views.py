from rest_framework.views import APIView
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .server import run_federated_rounds
from fraud_detection.models import FraudAlert
from audit_chain.chain import append_block


@method_decorator(csrf_exempt, name='dispatch')
class RunFederatedView(APIView):
    def post(self, request):
        try:
            results = run_federated_rounds(num_booths=4, num_rounds=3)

            # Last round's results → create FraudAlerts for flagged booths
            last_round = results[-1]
            alerts_created = 0

            for booth_id, n_flagged in enumerate(last_round['per_booth_flagged']):
                if n_flagged > 0:
                    FraudAlert.objects.create(
                        alert_type='duplicate_vote',
                        voter_id='FEDERATED_SCAN',
                        booth_id=f'BOOTH_{booth_id}',
                        description=(
                            f'Federated model flagged {n_flagged} anomalous '
                            f'verification patterns at booth {booth_id} '
                            f'in round {last_round["round"]}.'
                        ),
                        severity='medium',
                    )
                    alerts_created += 1

            # Log the federated run itself to the blockchain
            append_block(
                event_type='FEDERATED_SCAN_COMPLETE',
                data={
                    'rounds_completed': len(results),
                    'total_flagged':    last_round['total_flagged_across_booths'],
                    'alerts_created':   alerts_created,
                    'global_avg_score': last_round['global_avg_anomaly_score'],
                }
            )

            return Response({
                'status': 'success',
                'rounds': results,
                'alerts_created': alerts_created,
            })

        except Exception as e:
            return Response({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class FederatedResultsView(APIView):
    def get(self, request):
        import json, os
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'federated_results.json'
        )
        if not os.path.exists(path):
            return Response({'message': 'No federated results yet. POST to /run/ first.'})
        with open(path) as f:
            data = json.load(f)
        return Response(data)