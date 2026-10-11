from rest_framework.test import APIClient

from users.cognito import get_cognito
from users.models import User


def make_user(email, phone, role='customer'):
    return User.objects.create(
        first_name='Notif', last_name=role.capitalize(), email=email, phone=phone, neighborhood='Centro', city='Manaus',
        state='AM', address='Rua A', postal_code='69000000', role=role, cognito_sub=f'sub-{email}',
    )


def login(user):
    """An API client with the session cookie of `user`, the one the Cognito login would have set."""
    client = APIClient()
    client.cookies['jwt'] = get_cognito().client.make_access_token(user.cognito_sub)
    return client
