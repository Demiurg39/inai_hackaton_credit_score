import json
import os

import joblib
import numpy as np
import triton_python_backend_utils as pb_utils


class TritonPythonModel:
    def initialize(self, args):
        self.model_config = json.loads(args["model_config"])
        model_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(model_dir, "model.pkl")
        self.model = joblib.load(model_path)

    def execute(self, requests):
        responses = []
        for request in requests:
            in_tensor = pb_utils.get_input_tensor_by_name(request, "TEXT")
            input_texts = [t.decode("utf-8") for t in in_tensor.as_numpy().flatten()]
            predictions = self.model.predict(input_texts)
            out_tensor = pb_utils.Tensor(
                "CATEGORY",
                np.array([str(p).encode("utf-8") for p in predictions], dtype=object),
            )
            responses.append(pb_utils.InferenceResponse([out_tensor]))
        return responses

    def finalize(self):
        pass