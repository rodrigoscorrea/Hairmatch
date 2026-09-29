#!/bin/bash
# Runs on every LocalStack boot (ready hook). Resources are ephemeral by design.
set -e

BUCKET="${S3_BUCKET_NAME:-hairmatch-media}"
SENDER="${SES_SENDER_EMAIL:-no-reply@hairmatch.local}"

echo "Creating S3 bucket: ${BUCKET}"
awslocal s3 mb "s3://${BUCKET}" || true

echo "Verifying SES sender identity: ${SENDER}"
awslocal ses verify-email-identity --email-address "${SENDER}"

echo "LocalStack resources ready."
