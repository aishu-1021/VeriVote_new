import numpy as np


def generate_booth_data(booth_id: int, n_samples: int = 200, fraud_rate: float = 0.05):
    """
    Simulates voter verification event data for one booth.
    Each row is one verification attempt with 5 features.
    A small fraction are injected fraud patterns.
    """
    np.random.seed(booth_id * 42)

    # Normal verification patterns
    normal = np.column_stack([
        np.random.normal(30, 5, n_samples),       # avg time between verifications (mins)
        np.random.normal(85, 8, n_samples),        # match score
        np.random.randint(1, 4, n_samples),        # attempts before success
        np.random.normal(0, 1, n_samples),         # geographic deviation (km)
        np.random.randint(0, 2, n_samples),        # is_biometric_exempt
    ])

    # Fraud patterns — anomalous values injected
    n_fraud = int(n_samples * fraud_rate)
    fraud = np.column_stack([
        np.random.normal(2, 0.5, n_fraud),         # rapid successive verifications
        np.random.normal(20, 5, n_fraud),          # suspiciously low match scores
        np.random.randint(3, 6, n_fraud),          # many failed attempts
        np.random.normal(50, 10, n_fraud),         # far from booth jurisdiction
        np.ones(n_fraud),                          # all using biometric exemption
    ])

    data = np.vstack([normal, fraud])
    np.random.shuffle(data)
    return data