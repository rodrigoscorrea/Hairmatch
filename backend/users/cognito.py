import logging
from collections import namedtuple

import boto3
import requests
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings

logger = logging.getLogger(__name__)

POOL_NAME = 'hairmatch-dev'
APP_CLIENT_NAME = 'hairmatch-backend'
JWKS_TIMEOUT_SECONDS = 5

Tokens = namedtuple('Tokens', ['access_token', 'refresh_token'])


class CognitoError(Exception):
    def __init__(self, code=''):
        super().__init__(code)
        self.code = code


class InvalidPassword(CognitoError):
    pass


class UserAlreadyExists(CognitoError):
    pass


class InvalidCredentials(CognitoError):
    pass


class TooManyRequests(CognitoError):
    pass


class CognitoUnavailable(CognitoError):
    pass


class InvalidConfirmationCode(CognitoError):
    pass


class ExpiredConfirmationCode(CognitoError):
    pass


class UserNotConfirmed(CognitoError):
    pass


class AlreadyConfirmed(CognitoError):
    pass


class ResendRejected(CognitoError):
    pass


# Anything not listed here (including unknown ClientError codes) is CognitoUnavailable.
_ERRORS_BY_CODE = {
    'InvalidPasswordException': InvalidPassword,
    'UsernameExistsException': UserAlreadyExists,
    'NotAuthorizedException': InvalidCredentials,
    'UserNotFoundException': InvalidCredentials,
    'TooManyRequestsException': TooManyRequests,
    'LimitExceededException': TooManyRequests,
    'TooManyFailedAttemptsException': TooManyRequests,
    'CodeMismatchException': InvalidConfirmationCode,
    'ExpiredCodeException': ExpiredConfirmationCode,
    'UserNotConfirmedException': UserNotConfirmed,
}


def _username(email):
    # The pool ignores case (CaseSensitive=false), but the MiniStack emulator matches usernames exactly.
    return email.lower()


class CognitoService:
    """
    Every call to Cognito goes through here. boto3 errors become domain errors
    and each failure is logged with the operation and the error code only.
    """

    def __init__(self, client=None):
        self._client = client
        self._resolved_pool_id = None
        self._resolved_client_id = None

    @property
    def client(self):
        if self._client is None:
            self._client = boto3.client(
                'cognito-idp', config=Config(connect_timeout=5, read_timeout=10)
            )
        return self._client

    @property
    def pool_id(self):
        if settings.COGNITO_USER_POOL_ID:
            return settings.COGNITO_USER_POOL_ID
        if self._resolved_pool_id is None:
            self._resolved_pool_id = self._find_id(
                'list_user_pools', 'UserPools', 'Name', POOL_NAME, 'Id'
            )
        return self._resolved_pool_id

    @property
    def client_id(self):
        if settings.COGNITO_APP_CLIENT_ID:
            return settings.COGNITO_APP_CLIENT_ID
        if self._resolved_client_id is None:
            self._resolved_client_id = self._find_id(
                'list_user_pool_clients',
                'UserPoolClients',
                'ClientName',
                APP_CLIENT_NAME,
                'ClientId',
                UserPoolId=self.pool_id,
            )
        return self._resolved_client_id

    @property
    def issuer(self):
        return f'https://cognito-idp.{self.client.meta.region_name}.amazonaws.com/{self.pool_id}'

    def sign_up(self, email, password):
        email = _username(email)
        return self._call(
            'sign_up',
            ClientId=self.client_id,
            Username=email,
            Password=password,
            UserAttributes=[{'Name': 'email', 'Value': email}],
        )['UserSub']

    def sign_up_confirmed(self, email, password):
        sub = self.sign_up(email, password)
        try:
            self._call('admin_confirm_sign_up', UserPoolId=self.pool_id, Username=_username(email))
        except CognitoError:
            try:
                self.admin_delete_user(email)
            except CognitoError:
                pass
            raise
        return sub

    def confirm_sign_up(self, email, code):
        try:
            self._call(
                'confirm_sign_up',
                ClientId=self.client_id,
                Username=_username(email),
                ConfirmationCode=code,
            )
        except InvalidCredentials as exc:
            # The global table reads these codes as a login failure; here they mean something else.
            if exc.code == 'UserNotFoundException':
                raise InvalidConfirmationCode(exc.code) from exc
            raise AlreadyConfirmed(exc.code) from exc

    def resend_confirmation_code(self, email):
        try:
            self._call('resend_confirmation_code', ClientId=self.client_id, Username=_username(email))
        except CognitoUnavailable as exc:
            if exc.code == 'InvalidParameterException':
                raise ResendRejected(exc.code) from exc
            raise

    def authenticate(self, email, password):
        result = self._call(
            'initiate_auth',
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={'USERNAME': _username(email), 'PASSWORD': password},
            ClientId=self.client_id,
        )['AuthenticationResult']
        return Tokens(result['AccessToken'], result['RefreshToken'])

    def refresh(self, refresh_token):
        result = self._call(
            'initiate_auth',
            AuthFlow='REFRESH_TOKEN_AUTH',
            AuthParameters={'REFRESH_TOKEN': refresh_token},
            ClientId=self.client_id,
        )['AuthenticationResult']
        return result['AccessToken']

    def change_password(self, access_token, old_password, new_password):
        self._call(
            'change_password',
            AccessToken=access_token,
            PreviousPassword=old_password,
            ProposedPassword=new_password,
        )

    def revoke(self, refresh_token):
        self._call('revoke_token', Token=refresh_token, ClientId=self.client_id)

    def admin_delete_user(self, email):
        try:
            self._call('admin_delete_user', UserPoolId=self.pool_id, Username=_username(email))
        except InvalidCredentials as exc:
            if exc.code != 'UserNotFoundException':
                raise CognitoUnavailable(exc.code) from exc

    def admin_get_sub(self, email):
        try:
            response = self._call('admin_get_user', UserPoolId=self.pool_id, Username=_username(email))
        except InvalidCredentials as exc:
            if exc.code != 'UserNotFoundException':
                raise CognitoUnavailable(exc.code) from exc
            return None
        return next(
            attribute['Value']
            for attribute in response['UserAttributes']
            if attribute['Name'] == 'sub'
        )

    def admin_get_status(self, email):
        try:
            response = self._call('admin_get_user', UserPoolId=self.pool_id, Username=_username(email))
        except InvalidCredentials as exc:
            if exc.code != 'UserNotFoundException':
                raise CognitoUnavailable(exc.code) from exc
            return None
        return response['UserStatus']

    def fetch_jwks(self):
        # The in-memory test client publishes its own keys instead of serving them over HTTP.
        publish = getattr(self.client, 'jwks', None)
        if callable(publish):
            return publish()
        url = f'{self.client.meta.endpoint_url}/{self.pool_id}/.well-known/jwks.json'
        try:
            response = requests.get(url, timeout=JWKS_TIMEOUT_SECONDS)
            if response.status_code != 200:
                self._log('fetch_jwks', f'HTTP {response.status_code}')
                raise CognitoUnavailable(f'HTTP {response.status_code}')
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            self._log('fetch_jwks', type(exc).__name__)
            raise CognitoUnavailable(type(exc).__name__) from exc

    def _find_id(self, operation, results_key, name_key, name, id_key, **params):
        token = None
        while True:
            kwargs = dict(params, MaxResults=60)
            if token:
                kwargs['NextToken'] = token
            response = self._call(operation, **kwargs)
            for item in response[results_key]:
                if item[name_key] == name:
                    return item[id_key]
            token = response.get('NextToken')
            if not token:
                self._log(operation, f'{name} not found')
                raise CognitoUnavailable(f'{name} not found')

    def _call(self, operation, **kwargs):
        try:
            return getattr(self.client, operation)(**kwargs)
        except ClientError as exc:
            code = exc.response.get('Error', {}).get('Code', '')
            self._log(operation, code)
            raise _ERRORS_BY_CODE.get(code, CognitoUnavailable)(code) from exc
        except BotoCoreError as exc:
            code = type(exc).__name__
            self._log(operation, code)
            raise CognitoUnavailable(code) from exc

    @staticmethod
    def _log(operation, code):
        logger.warning('cognito %s failed: %s', operation, code)


_service = None


def get_cognito():
    global _service
    if _service is None:
        client = None
        if settings.COGNITO_USE_FAKE:
            from .cognito_fake import FakeCognitoIdp

            client = FakeCognitoIdp()
        _service = CognitoService(client)
    return _service


def reset_cognito():
    global _service
    _service = None
