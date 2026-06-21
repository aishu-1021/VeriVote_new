import numpy as np
import flwr as fl
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from .data import generate_booth_data


def get_model_params(model: IsolationForest):
    """Extract serializable params from trained IsolationForest."""
    params = []
    for estimator in model.estimators_:
        params.append(estimator.tree_.threshold.astype(np.float32))
    return params


def set_model_params(model: IsolationForest, params):
    """Not used for IsolationForest — each booth trains independently."""
    pass


class BoothClient(fl.client.NumPyClient):
    def __init__(self, booth_id: int):
        self.booth_id = booth_id
        self.model = IsolationForest(
            n_estimators=50,
            contamination=0.05,
            random_state=booth_id,
        )
        self.scaler = StandardScaler()
        self.data = generate_booth_data(booth_id)

    def get_parameters(self, config):
        """Return local model score as a single parameter array."""
        X_scaled = self.scaler.fit_transform(self.data)
        self.model.fit(X_scaled)
        scores = self.model.score_samples(X_scaled).astype(np.float32)
        return [scores]

    def fit(self, parameters, config):
        """Train on local data."""
        X_scaled = self.scaler.fit_transform(self.data)
        self.model.fit(X_scaled)
        scores = self.model.score_samples(X_scaled).astype(np.float32)
        print(f"[Booth {self.booth_id}] Trained on {len(self.data)} samples.")
        return [scores], len(self.data), {}

    def evaluate(self, parameters, config):
        """Evaluate local anomaly detection."""
        X_scaled = self.scaler.transform(self.data)
        scores = self.model.score_samples(X_scaled)
        threshold = np.percentile(scores, 5)
        n_flagged = np.sum(scores < threshold)
        loss = float(-np.mean(scores))
        print(f"[Booth {self.booth_id}] Flagged {n_flagged} anomalies.")
        return loss, len(self.data), {"flagged": int(n_flagged)}


def get_client_fn(booth_id: int):
    def client_fn(cid: str):
        return BoothClient(booth_id=booth_id).to_client()
    return client_fn