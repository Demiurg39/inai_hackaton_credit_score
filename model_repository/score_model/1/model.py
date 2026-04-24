"""
model_repository/score_model/1/model.py
Triton Python backend model for credit scoring.
Loads joblib model (w, mu, sd, feature_cols) and runs inference.
"""
import os

import joblib
import numpy as np
from scipy.special import expit  # numerically stable sigmoid
import triton_python_backend_utils as pb_utils


class TritonPythonModel:
    def initialize(self, args):
        model_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(model_dir, "model.joblib")
        self.data = joblib.load(model_path)
        self.w = self.data["w"]           # shape (n_features + 1,) with bias
        self.mu = self.data["mu"]        # shape (n_features,)
        self.sd = self.data["sd"]        # shape (n_features,)
        self.feature_cols = self.data["feature_cols"]

    def execute(self, requests):
        responses = []
        for request in requests:
            try:
                in_tensor = pb_utils.get_input_tensor_by_name(request, "INPUT")
                inp = in_tensor.as_numpy().astype(np.float64)

                # Scale using training statistics
                scaled = (inp - self.mu) / self.sd

                # Add bias column (ones)
                ones_col = np.ones((scaled.shape[0], 1), dtype=np.float64)
                Xm = np.concatenate([ones_col, scaled], axis=1)

                # Compute logit, clip for stability, apply sigmoid
                logits = np.clip(Xm @ self.w, -30, 30)
                p_bad = expit(logits)   # 1 / (1 + exp(-logits))

                # Labels: 1=bad, 0=good
                labels = np.array([[1.0 if p >= 0.5 else 0.0] for p in p_bad.flat])
                labels = labels.reshape(-1, 1).astype(np.float64)
                p_bad_2d = p_bad.reshape(-1, 1)
                p_good_2d = (1 - p_bad).reshape(-1, 1)

                # Concatenate: [p_bad, p_good, label]
                out = np.concatenate([p_bad_2d, p_good_2d, labels], axis=1)

                out_tensor = pb_utils.Tensor(
                    "OUTPUT",
                    out,
                )
                responses.append(pb_utils.InferenceResponse([out_tensor]))
            except Exception as e:
                # Return error response
                err_out = np.array([[-1.0, -1.0, -1.0]])
                err_tensor = pb_utils.Tensor("OUTPUT", err_out)
                responses.append(pb_utils.InferenceResponse([err_tensor]))
        return responses