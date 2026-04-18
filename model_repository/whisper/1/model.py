import base64
import os
import tempfile

import numpy as np
import triton_python_backend_utils as pb_utils
import whisper


class TritonPythonModel:
    def initialize(self, args):
        model_name = os.getenv("WHISPER_MODEL", "small")
        self.model = whisper.load_model(model_name)

    def execute(self, requests):
        responses = []
        for request in requests:
            in_tensor = pb_utils.get_input_tensor_by_name(request, "audio_bytes")
            audio_b64 = in_tensor.as_numpy().flatten()[0].decode("utf-8")
            audio_bytes = base64.b64decode(audio_b64)

            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
                f.write(audio_bytes)
                f.flush()
                audio_path = f.name

            try:
                result = self.model.transcribe(audio_path, fp16=False)
                transcript = result["text"].strip()
            finally:
                os.unlink(audio_path)

            out_tensor = pb_utils.Tensor(
                "transcript",
                np.array([transcript.encode("utf-8")], dtype=object),
            )
            responses.append(pb_utils.InferenceResponse([out_tensor]))
        return responses

    def finalize(self):
        pass