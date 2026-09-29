#!/bin/bash
# Runs on every LocalStack boot (ready hook). Resources are ephemeral by design.
set -e

BUCKET="${S3_BUCKET_NAME:-dev-hairmatch-media}"
SENDER="${SES_SENDER_EMAIL:-no-reply@hairmatch.local}"

echo "Creating S3 bucket: ${BUCKET}"
awslocal s3 mb "s3://${BUCKET}" || true

echo "Allowing frontend GETs on ${BUCKET} (CORS)"
awslocal s3api put-bucket-cors --bucket "${BUCKET}" --cors-configuration '{
  "CORSRules": [
    {
      "AllowedOrigins": ["*"],
      "AllowedMethods": ["GET", "HEAD"],
      "AllowedHeaders": ["*"],
      "MaxAgeSeconds": 3000
    }
  ]
}'

echo "Making ${BUCKET} objects publicly readable"
awslocal s3api put-bucket-policy --bucket "${BUCKET}" --policy '{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadMedia",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::'"${BUCKET}"'/*"
    }
  ]
}'

echo "Verifying SES sender identity: ${SENDER}"
awslocal ses verify-email-identity --email-address "${SENDER}"

echo "LocalStack resources ready."
