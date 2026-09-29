import datetime

import jwt
from django.conf import settings

SIGNUP_TOKEN_TTL = datetime.timedelta(minutes=30)
SIGNUP_TOKEN_PURPOSE = 'google_signup'


class InvalidSignupToken(Exception):
    pass


def issue_session_token(user):
    """Session of a Google account, the only accounts the backend still signs sessions for."""
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        'id': user.id,
        'iss': 'hairmatch',
        'token_use': 'session',
        'iat': now,
        'exp': now + datetime.timedelta(minutes=60),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')


def set_session_cookie(response, user):
    response.set_cookie(
        key='jwt',
        value=issue_session_token(user),
        max_age=ACCESS_COOKIE_MAX_AGE,
        httponly=True,
        samesite='None',
        secure=True,
    )
    return response


ACCESS_COOKIE_MAX_AGE = 3600
REFRESH_COOKIE_MAX_AGE = 30 * 24 * 3600
REFRESH_COOKIE_PATH = '/api/auth/'


def set_access_cookie(response, access_token):
    response.set_cookie(
        key='jwt',
        value=access_token,
        max_age=ACCESS_COOKIE_MAX_AGE,
        httponly=True,
        samesite='None',
        secure=True,
    )
    return response


def set_cognito_cookies(response, tokens):
    set_access_cookie(response, tokens.access_token)
    response.set_cookie(
        key='refresh_token',
        value=tokens.refresh_token,
        max_age=REFRESH_COOKIE_MAX_AGE,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        samesite='None',
        secure=True,
    )
    return response


def clear_auth_cookies(response):
    # Expire with the same attributes the cookies were set with: browsers match on path
    # and reject a SameSite=None cookie that is not Secure.
    for key, path in (('jwt', '/'), ('refresh_token', REFRESH_COOKIE_PATH)):
        response.set_cookie(
            key=key,
            value='',
            max_age=0,
            expires='Thu, 01 Jan 1970 00:00:00 GMT',
            path=path,
            httponly=True,
            samesite='None',
            secure=True,
        )
    return response


def create_signup_token(email, sub):
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        'email': email,
        'sub': sub,
        'purpose': SIGNUP_TOKEN_PURPOSE,
        'iat': now,
        'exp': now + SIGNUP_TOKEN_TTL,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')


def decode_signup_token(token):
    try:
        claims = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
    except jwt.InvalidTokenError as err:
        raise InvalidSignupToken(str(err)) from err
    if claims.get('purpose') != SIGNUP_TOKEN_PURPOSE:
        raise InvalidSignupToken('Unexpected token purpose')
    return claims
