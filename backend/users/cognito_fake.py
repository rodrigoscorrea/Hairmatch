"""
In-memory stand-in for ``boto3.client('cognito-idp')``, used by the test suite.

It answers with the same response shapes and raises the same
``botocore.exceptions.ClientError`` codes as Cognito, so the real error mapping
and the real JWKS verification run in tests. Tokens are RS256 JWTs signed with a
key generated once per process; ``jwks()`` publishes the matching public key.
"""
import json
import re
import time
import uuid
from collections import defaultdict, deque
from types import SimpleNamespace

import jwt
from botocore.exceptions import ClientError
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

REGION = 'us-east-2'
POOL_NAME = 'hairmatch-dev'
CLIENT_NAME = 'hairmatch-backend'
POOL_ID = f'{REGION}_FakePool1'
CLIENT_ID = 'fakeclientid0123456789'
KID = 'fake-key-1'
ACCESS_TOKEN_TTL = 3600
REFRESH_TOKEN_TTL = 30 * 24 * 3600

PASSWORD_MIN_LENGTH = 8


def new_rsa_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


_SIGNING_KEY = new_rsa_key()


def issuer():
    return f'https://cognito-idp.{REGION}.amazonaws.com/{POOL_ID}'


def _client_error(code, operation, message=''):
    return ClientError({'Error': {'Code': code, 'Message': message or code}}, operation)


def _meets_password_policy(password):
    return (
        len(password) >= PASSWORD_MIN_LENGTH
        and re.search(r'[A-Z]', password) is not None
        and re.search(r'[a-z]', password) is not None
        and re.search(r'\d', password) is not None
    )


class FakeCognitoIdp:
    def __init__(self):
        self.meta = SimpleNamespace(
            region_name=REGION,
            endpoint_url=f'https://cognito-idp.{REGION}.amazonaws.com',
        )
        self.users = {}
        self.refresh_tokens = {}
        self.access_tokens = {}
        self.calls = []
        self._failures = defaultdict(deque)

    # -- test helpers -------------------------------------------------------

    def jwks(self):
        jwk = json.loads(RSAAlgorithm.to_jwk(_SIGNING_KEY.public_key()))
        jwk.update({'kid': KID, 'alg': 'RS256', 'use': 'sig'})
        return {'keys': [jwk]}

    def make_access_token(self, sub, signing_key=None, headers=None, **claims):
        """Build an access token; a claim passed as ``None`` is dropped."""
        now = int(time.time())
        payload = {
            'sub': sub,
            'iss': issuer(),
            'token_use': 'access',
            'client_id': CLIENT_ID,
            'username': sub,
            'scope': 'aws.cognito.signin.user.admin',
            'jti': str(uuid.uuid4()),
            'iat': now,
            'exp': now + ACCESS_TOKEN_TTL,
        }
        payload.update(claims)
        payload = {key: value for key, value in payload.items() if value is not None}
        header = {'kid': KID}
        header.update(headers or {})
        return jwt.encode(
            payload, signing_key or _SIGNING_KEY, algorithm='RS256', headers=header
        )

    def make_refresh_token(self, sub):
        """Build a refresh token the way MiniStack does: a signed JWT with token_use=refresh."""
        now = int(time.time())
        token = self.make_access_token(
            sub, token_use='refresh', exp=now + REFRESH_TOKEN_TTL, scope=None
        )
        self.refresh_tokens[token] = sub
        return token

    def _issue_access_token(self, sub):
        token = self.make_access_token(sub)
        self.access_tokens[token] = sub
        return token

    def fail_next(self, operation, error):
        """Make the next ``operation`` call raise ``error`` (an exception or a Cognito error code)."""
        self._failures[operation].append(error)

    def _begin(self, operation, **kwargs):
        self.calls.append((operation, kwargs))
        queue = self._failures[operation]
        if queue:
            error = queue.popleft()
            if isinstance(error, str):
                raise _client_error(error, operation)
            raise error

    # -- pool discovery -----------------------------------------------------

    def list_user_pools(self, MaxResults=60, **kwargs):
        self._begin('list_user_pools', MaxResults=MaxResults)
        return {'UserPools': [{'Id': POOL_ID, 'Name': POOL_NAME}]}

    def list_user_pool_clients(self, UserPoolId, MaxResults=60, **kwargs):
        self._begin('list_user_pool_clients', UserPoolId=UserPoolId)
        return {
            'UserPoolClients': [
                {'ClientId': CLIENT_ID, 'ClientName': CLIENT_NAME, 'UserPoolId': POOL_ID}
            ]
        }

    # -- users --------------------------------------------------------------

    def sign_up(self, ClientId, Username, Password, UserAttributes=None, **kwargs):
        self._begin('sign_up', ClientId=ClientId, Username=Username)
        if not _meets_password_policy(Password):
            raise _client_error('InvalidPasswordException', 'SignUp')
        key = Username.lower()
        if key in self.users:
            raise _client_error('UsernameExistsException', 'SignUp')
        sub = str(uuid.uuid4())
        self.users[key] = {
            'sub': sub,
            'email': Username,
            'password': Password,
            'confirmed': False,
        }
        return {'UserConfirmed': False, 'UserSub': sub}

    def admin_confirm_sign_up(self, UserPoolId, Username, **kwargs):
        self._begin('admin_confirm_sign_up', UserPoolId=UserPoolId, Username=Username)
        self._get_user(Username, 'AdminConfirmSignUp')['confirmed'] = True
        return {}

    def admin_delete_user(self, UserPoolId, Username, **kwargs):
        self._begin('admin_delete_user', UserPoolId=UserPoolId, Username=Username)
        user = self._get_user(Username, 'AdminDeleteUser')
        del self.users[user['email'].lower()]
        for token, sub in list(self.refresh_tokens.items()):
            if sub == user['sub']:
                del self.refresh_tokens[token]
        return {}

    def admin_get_user(self, UserPoolId, Username, **kwargs):
        self._begin('admin_get_user', UserPoolId=UserPoolId, Username=Username)
        user = self._get_user(Username, 'AdminGetUser')
        return {
            'Username': user['sub'],
            'UserStatus': 'CONFIRMED' if user['confirmed'] else 'UNCONFIRMED',
            'UserAttributes': [
                {'Name': 'sub', 'Value': user['sub']},
                {'Name': 'email', 'Value': user['email']},
            ],
        }

    def _get_user(self, username, operation):
        user = self.users.get(username.lower())
        if user is None:
            raise _client_error('UserNotFoundException', operation)
        return user

    # -- authentication -----------------------------------------------------

    def initiate_auth(self, AuthFlow, AuthParameters, ClientId, **kwargs):
        self._begin('initiate_auth', AuthFlow=AuthFlow, ClientId=ClientId)
        if AuthFlow == 'USER_PASSWORD_AUTH':
            user = self._get_user(AuthParameters['USERNAME'], 'InitiateAuth')
            if user['password'] != AuthParameters['PASSWORD']:
                raise _client_error('NotAuthorizedException', 'InitiateAuth')
            if not user['confirmed']:
                raise _client_error('UserNotConfirmedException', 'InitiateAuth')
            access_token = self._issue_access_token(user['sub'])
            return {
                'AuthenticationResult': {
                    'AccessToken': access_token,
                    'RefreshToken': self.make_refresh_token(user['sub']),
                    'ExpiresIn': ACCESS_TOKEN_TTL,
                    'TokenType': 'Bearer',
                }
            }
        if AuthFlow == 'REFRESH_TOKEN_AUTH':
            sub = self.refresh_tokens.get(AuthParameters.get('REFRESH_TOKEN'))
            if sub is None:
                raise _client_error('NotAuthorizedException', 'InitiateAuth')
            return {
                'AuthenticationResult': {
                    'AccessToken': self._issue_access_token(sub),
                    'ExpiresIn': ACCESS_TOKEN_TTL,
                    'TokenType': 'Bearer',
                }
            }
        raise _client_error('InvalidParameterException', 'InitiateAuth')

    def change_password(self, PreviousPassword, ProposedPassword, AccessToken, **kwargs):
        self._begin('change_password')
        sub = self.access_tokens.get(AccessToken)
        user = next((u for u in self.users.values() if u['sub'] == sub), None)
        if user is None or user['password'] != PreviousPassword:
            raise _client_error('NotAuthorizedException', 'ChangePassword')
        if not _meets_password_policy(ProposedPassword):
            raise _client_error('InvalidPasswordException', 'ChangePassword')
        user['password'] = ProposedPassword
        return {}

    def revoke_token(self, Token, ClientId, **kwargs):
        self._begin('revoke_token', ClientId=ClientId)
        self.refresh_tokens.pop(Token, None)
        return {}
