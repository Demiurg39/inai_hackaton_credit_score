#!/bin/bash
set -e

echo "Syncing models from R2..."
rclone sync "AWS_BUCKET:/${BUCKET_NAME}/models" /models \
  --s3-endpoint="${AWS_ENDPOINT_URL_S3}" \
  --s3-access-key-id="${AWS_ACCESS_KEY_ID}" \
  --s3-secret-access-key="${AWS_SECRET_ACCESS_KEY}" \
  --s3-region="${AWS_REGION}" \
  --s3-no-check-bucket \
  --log-level INFO

echo "Models synced. Starting Triton..."
exec tritonserver --model-repository=/models "$@"