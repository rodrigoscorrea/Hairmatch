"""Helpers for tests that register an account through the API and then use it."""
from .cognito import get_cognito
from .models import User


def activate_account(email):
    """Confirm a pending e-mail account the way the e-mailed code would: in the pool and in the database."""
    get_cognito().client.admin_confirm_sign_up(UserPoolId='test-pool', Username=email)
    User.objects.filter(email__iexact=email).update(is_active=True)
