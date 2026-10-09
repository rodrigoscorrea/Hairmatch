#!/bin/bash
# Runs on every MiniStack boot (ready hook). Idempotent: state is persisted in a volume, so the pool and
# the app client are created only when missing, and then both are brought to the settings below, so a
# volume created before a setting existed gets it on the next boot.
set -e

POOL_NAME="hairmatch-dev"
CLIENT_NAME="hairmatch-backend"
PASSWORD_POLICY='PasswordPolicy={MinimumLength=8,RequireUppercase=true,RequireLowercase=true,RequireNumbers=true,RequireSymbols=false}'
# The code e-mail Cognito sends at sign-up and on resend. MiniStack records it in its own SES
# (GET http://localhost:4567/_ministack/ses/messages) and always uses the code 123456.
VERIFICATION_TEMPLATE='{"DefaultEmailOption":"CONFIRM_WITH_CODE","EmailSubject":"Hairmatch: confirme seu e-mail","EmailMessage":"Seu código de confirmação do Hairmatch é {####}. Ele vale por 24 horas."}'

POOL_ID=$(awslocal cognito-idp list-user-pools --max-results 60 \
  --query "UserPools[?Name=='${POOL_NAME}'].Id | [0]" --output text)

if [ -z "${POOL_ID}" ] || [ "${POOL_ID}" = "None" ]; then
  echo "Creating Cognito user pool: ${POOL_NAME}"
  POOL_ID=$(awslocal cognito-idp create-user-pool \
    --pool-name "${POOL_NAME}" \
    --username-attributes email \
    --username-configuration CaseSensitive=false \
    --query "UserPool.Id" --output text)
else
  echo "Cognito user pool ${POOL_NAME} already exists: ${POOL_ID}"
fi

# update-user-pool puts back the default of every attribute it is not given: pass all of them.
awslocal cognito-idp update-user-pool \
  --user-pool-id "${POOL_ID}" \
  --auto-verified-attributes email \
  --policies "${PASSWORD_POLICY}" \
  --verification-message-template "${VERIFICATION_TEMPLATE}"

CLIENT_ID=$(awslocal cognito-idp list-user-pool-clients --user-pool-id "${POOL_ID}" --max-results 60 \
  --query "UserPoolClients[?ClientName=='${CLIENT_NAME}'].ClientId | [0]" --output text)

if [ -z "${CLIENT_ID}" ] || [ "${CLIENT_ID}" = "None" ]; then
  echo "Creating Cognito app client: ${CLIENT_NAME}"
  CLIENT_ID=$(awslocal cognito-idp create-user-pool-client \
    --user-pool-id "${POOL_ID}" \
    --client-name "${CLIENT_NAME}" \
    --no-generate-secret \
    --query "UserPoolClient.ClientId" --output text)
else
  echo "Cognito app client ${CLIENT_NAME} already exists: ${CLIENT_ID}"
fi

# Same rule as the pool: pass every attribute. PreventUserExistenceErrors makes an unknown user look
# like a wrong code or password, so the confirmation routes do not tell which e-mails have accounts.
awslocal cognito-idp update-user-pool-client \
  --user-pool-id "${POOL_ID}" \
  --client-id "${CLIENT_ID}" \
  --client-name "${CLIENT_NAME}" \
  --explicit-auth-flows ALLOW_USER_PASSWORD_AUTH ALLOW_REFRESH_TOKEN_AUTH \
  --access-token-validity 60 \
  --refresh-token-validity 30 \
  --token-validity-units AccessToken=minutes,RefreshToken=days \
  --prevent-user-existence-errors ENABLED > /dev/null

echo "Cognito ready. COGNITO_USER_POOL_ID=${POOL_ID} COGNITO_APP_CLIENT_ID=${CLIENT_ID}"
