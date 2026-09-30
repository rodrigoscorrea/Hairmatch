import json
from collections import namedtuple

import jwt
from django.conf import settings
from django.http import JsonResponse
from jwt.algorithms import RSAAlgorithm

from .cognito import CognitoUnavailable, get_cognito
from .models import Customer, Hairdresser, User

SESSION_ISSUER = 'hairmatch'
INVALID_SESSION_MESSAGE = 'Sessão inválida ou expirada.'
AUTH_UNAVAILABLE_MESSAGE = 'Serviço de autenticação indisponível. Tente novamente em instantes.'
FORBIDDEN_MESSAGE = 'Você não tem permissão para acessar este recurso.'

SessionUser = namedtuple('SessionUser', ['user', 'provider', 'access_token'])

# kid -> RSA public key, per process
_jwks_keys = {}


def clear_jwks_cache():
    _jwks_keys.clear()


def authenticate_request(request):
    """
    Returns the SessionUser for the `jwt` cookie, or None when it is missing or invalid.
    Raises CognitoUnavailable only when the Cognito signing keys cannot be fetched.
    """
    return authenticate_token(request.COOKIES.get('jwt'))


def authenticate_token(token):
    """Same as authenticate_request, for a token that did not come from the cookie."""
    if not token:
        return None
    try:
        header = jwt.get_unverified_header(token)
        claims = jwt.decode(token, options={'verify_signature': False})
    except jwt.InvalidTokenError:
        return None

    issuer = claims.get('iss')
    if issuer == SESSION_ISSUER:
        return _authenticate_google(token, header)
    if isinstance(issuer, str) and issuer == get_cognito().issuer:
        return _authenticate_cognito(token, header)
    return None


def authenticated_user(request):
    """Returns (SessionUser, None) or (None, JsonResponse) with the 401/503 to send back."""
    try:
        session = authenticate_request(request)
    except CognitoUnavailable:
        return None, JsonResponse({'error': AUTH_UNAVAILABLE_MESSAGE}, status=503)
    if session is None:
        return None, JsonResponse({'error': INVALID_SESSION_MESSAGE}, status=401)
    return session, None


def forbidden():
    """403 for a valid session that does not own the resource."""
    return JsonResponse({'error': FORBIDDEN_MESSAGE}, status=403)


def authenticated_hairdresser(request):
    """Returns (SessionUser, Hairdresser, None) or (None, None, JsonResponse): 401/503 without a session, 403 for non-hairdressers."""
    return _authenticated_profile(request, Hairdresser, 'Apenas profissionais podem realizar esta ação.')


def authenticated_customer(request):
    """Returns (SessionUser, Customer, None) or (None, None, JsonResponse): 401/503 without a session, 403 for non-customers."""
    return _authenticated_profile(request, Customer, 'Apenas clientes podem realizar esta ação.')


def is_own_email(session, email):
    """Whether the e-mail in the URL is the session user's. Case-insensitive, since Cognito lowercases usernames."""
    return isinstance(email, str) and email.lower() == session.user.email.lower()


def _authenticated_profile(request, model, message):
    session, error = authenticated_user(request)
    if error:
        return None, None, error
    profile = model.objects.filter(user_id=session.user.id).first()
    if profile is None:
        return None, None, JsonResponse({'error': message}, status=403)
    return session, profile, None


def _authenticate_cognito(token, header):
    if header.get('alg') != 'RS256':
        return None
    key = _signing_key(header.get('kid'))
    if key is None:
        return None
    cognito = get_cognito()
    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=['RS256'],
            issuer=cognito.issuer,
            options={'require': ['exp', 'iss', 'sub', 'token_use', 'client_id']},
        )
    except jwt.InvalidTokenError:
        return None
    if claims['token_use'] != 'access' or claims['client_id'] != cognito.client_id:
        return None
    user = User.objects.filter(cognito_sub=claims['sub'], is_active=True).first()
    return SessionUser(user, 'cognito', token) if user else None


def _authenticate_google(token, header):
    if header.get('alg') != 'HS256':
        return None
    try:
        claims = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=['HS256'],
            issuer=SESSION_ISSUER,
            options={'require': ['exp', 'iss', 'token_use', 'id']},
        )
    except jwt.InvalidTokenError:
        return None
    if claims['token_use'] != 'session' or not isinstance(claims['id'], int):
        return None
    user = User.objects.filter(id=claims['id'], is_active=True).first()
    return SessionUser(user, 'google', token) if user else None


def _signing_key(kid):
    """Cached key for `kid`. A kid that is not cached triggers one JWKS fetch."""
    if kid not in _jwks_keys:
        _load_jwks()
    return _jwks_keys.get(kid)


def _load_jwks():
    jwks = get_cognito().fetch_jwks()
    try:
        keys = {
            jwk['kid']: RSAAlgorithm.from_jwk(json.dumps(jwk))
            for jwk in jwks['keys']
            if jwk.get('kty') == 'RSA'
        }
    except (KeyError, TypeError, ValueError, jwt.PyJWTError) as exc:
        raise CognitoUnavailable('MalformedJwks') from exc
    _jwks_keys.clear()
    _jwks_keys.update(keys)
