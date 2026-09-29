from unittest import TextTestResult

from django.test.runner import DiscoverRunner

from users.authentication import clear_jwks_cache
from users.cognito import reset_cognito


class CognitoResetMixin:
    """Database changes roll back between tests, so the in-memory Cognito and the key cache must too."""

    def startTest(self, test):
        reset_cognito()
        clear_jwks_cache()
        super().startTest(test)


class HairmatchTestRunner(DiscoverRunner):
    def get_resultclass(self):
        base = super().get_resultclass() or TextTestResult
        return type('CognitoResetResult', (CognitoResetMixin, base), {})
