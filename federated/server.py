import numpy as np
import json
import os
import flwr as fl


def run_federated_rounds(num_booths: int = 4, num_rounds: int = 3):
    """
    Simulates federated learning across num_booths booths.
    Returns aggregated anomaly scores per round.
    """
    from .client import BoothClient

    print(f"\n{'='*50}")
    print(f"Starting Federated Learning: {num_booths} booths, {num_rounds} rounds")
    print(f"{'='*50}\n")

    all_round_results = []

    for round_num in range(1, num_rounds + 1):
        print(f"\n--- Round {round_num}/{num_rounds} ---")
        round_scores = []
        round_flagged = []

        for booth_id in range(num_booths):
            client = BoothClient(booth_id=booth_id)

            # Local training
            params, n_samples, _ = client.fit(parameters=[], config={})
            scores = params[0]  # anomaly scores array

            # Local evaluation
            loss, _, metrics = client.evaluate(parameters=[], config={})

            round_scores.append(float(np.mean(scores)))
            round_flagged.append(metrics['flagged'])

            print(f"  Booth {booth_id}: avg_score={np.mean(scores):.4f}, "
                  f"flagged={metrics['flagged']}")

        # FedAvg — average the anomaly scores across booths
        global_avg_score = float(np.mean(round_scores))
        total_flagged = sum(round_flagged)

        round_result = {
            'round': round_num,
            'global_avg_anomaly_score': global_avg_score,
            'total_flagged_across_booths': total_flagged,
            'per_booth_flagged': round_flagged,
        }
        all_round_results.append(round_result)

        print(f"\n  [FedAvg] Global avg score: {global_avg_score:.4f}")
        print(f"  [FedAvg] Total flagged: {total_flagged}")

    # Save results
    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'federated_results.json'
    )
    with open(output_path, 'w') as f:
        json.dump(all_round_results, f, indent=2)

    print(f"\n{'='*50}")
    print(f"Federated learning complete. Results saved to federated_results.json")
    print(f"{'='*50}\n")

    return all_round_results


if __name__ == '__main__':
    run_federated_rounds(num_booths=4, num_rounds=3)