from django.conf import settings
from google.auth.exceptions import GoogleAuthError
from google.auth.transport import requests
from google.oauth2 import id_token


class GoogleTokenError(Exception):
    pass


def verify_google_id_token(token):
    try:
        # verify_oauth2_token accepts a single audience; the list is checked below.
        claims = id_token.verify_oauth2_token(token, requests.Request(), audience=None)
    except (ValueError, GoogleAuthError) as err:
        raise GoogleTokenError(str(err)) from err

    if claims.get('aud') not in settings.GOOGLE_OAUTH_CLIENT_IDS:
        raise GoogleTokenError('Token audience is not an accepted client ID')

    email_verified = claims.get('email_verified')
    return {
        'sub': claims['sub'],
        'email': claims.get('email', ''),
        'email_verified': email_verified is True or email_verified == 'true',
        'given_name': claims.get('given_name', ''),
        'family_name': claims.get('family_name', ''),
    }
