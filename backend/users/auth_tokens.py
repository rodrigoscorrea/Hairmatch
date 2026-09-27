import datetime

import jwt
from django.conf import settings

SIGNUP_TOKEN_TTL = datetime.timedelta(minutes=30)
SIGNUP_TOKEN_PURPOSE = 'google_signup'


class InvalidSignupToken(Exception):
    pass


def issue_session_token(user):
    now = datetime.datetime.now()
    payload = {
        'id': user.id,
        'exp': now + datetime.timedelta(minutes=60),
        'iat': now,
    }
    return jwt.encode(payload, 'secret', algorithm='HS256')


def set_session_cookie(response, user):
    response.set_cookie(
        key='jwt',
        value=issue_session_token(user),
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
