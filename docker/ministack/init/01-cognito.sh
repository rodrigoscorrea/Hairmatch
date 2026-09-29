#!/bin/bash
# Runs on every MiniStack boot (ready hook). Idempotent: state is persisted in a volume,
# so the pool and the app client are created only when the pool is missing.
set -e

POOL_NAME="hairmatch-dev"
CLIENT_NAME="hairmatch-backend"

POOL_ID=$(awslocal cognito-idp list-user-pools --max-results 60 \
  --query "UserPools[?Name=='${POOL_NAME}'].Id | [0]" --output text)

if [ -n "${POOL_ID}" ] && [ "${POOL_ID}" != "None" ]; then
  echo "Cognito user pool ${POOL_NAME} already exists: ${POOL_ID}"
  exit 0
fi

echo "Creating Cognito user pool: ${POOL_NAME}"
POOL_ID=$(awslocal cognito-idp create-user-pool \
  --pool-name "${POOL_NAME}" \
  --username-attributes email \
  --username-configuration CaseSensitive=false \
  --auto-verified-attributes email \
  --policies 'PasswordPolicy={MinimumLength=8,RequireUppercase=true,RequireLowercase=true,RequireNumbers=true,RequireSymbols=false}' \
  --query "UserPool.Id" --output text)

echo "Creating Cognito app client: ${CLIENT_NAME}"
CLIENT_ID=$(awslocal cognito-idp create-user-pool-client \
  --user-pool-id "${POOL_ID}" \
  --client-name "${CLIENT_NAME}" \
  --no-generate-secret \
  --explicit-auth-flows ALLOW_USER_PASSWORD_AUTH ALLOW_REFRESH_TOKEN_AUTH \
  --access-token-validity 60 \
  --refresh-token-validity 30 \
  --token-validity-units AccessToken=minutes,RefreshToken=days \
  --query "UserPoolClient.ClientId" --output text)

echo "Cognito ready. COGNITO_USER_POOL_ID=${POOL_ID} COGNITO_APP_CLIENT_ID=${CLIENT_ID}"
