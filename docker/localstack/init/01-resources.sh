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

# SNS Mobile Push. LocalStack accepts any credential, so a fake FCM service account stands in for the real one.
# The region is explicit so the platform application lives where the backend looks for it.
PUSH_REGION="${AWS_DEFAULT_REGION:-us-east-2}"
PUSH_APP="hairmatch-dev-fcm"
if awslocal sns list-platform-applications --region "${PUSH_REGION}" --query 'PlatformApplications[].PlatformApplicationArn' --output text | grep -q "/GCM/${PUSH_APP}\b"; then
  echo "SNS platform application already exists: ${PUSH_APP}"
else
  echo "Creating SNS platform application: ${PUSH_APP}"
  # JSON syntax: the shorthand parser of the CLI rejects the quotes of the credential. LocalStack also wants a principal, which real FCM v1 does not use.
  FAKE_CREDENTIAL='{\"type\":\"service_account\",\"project_id\":\"hairmatch-dev\",\"private_key_id\":\"fake\",\"private_key\":\"fake\",\"client_email\":\"fake@hairmatch-dev.iam.gserviceaccount.com\",\"client_id\":\"0\"}'
  awslocal sns create-platform-application --region "${PUSH_REGION}" --name "${PUSH_APP}" --platform GCM \
    --attributes "{\"PlatformCredential\":\"${FAKE_CREDENTIAL}\",\"PlatformPrincipal\":\"fake\"}"
fi

echo "LocalStack resources ready."
