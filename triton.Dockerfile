FROM nvcr.io/nvidia/tritonserver:24.03-py3

RUN pip install --no-cache-dir scikit-learn joblib