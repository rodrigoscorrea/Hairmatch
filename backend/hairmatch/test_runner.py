from unittest import TextTestResult

from django.core.cache import cache
from django.test.runner import DiscoverRunner

from users.authentication import clear_jwks_cache
from users.cognito import reset_cognito


class CognitoResetMixin:
    """Database changes roll back between tests, so the in-memory Cognito, the key cache and the throttle counters must too."""

    def startTest(self, test):
        reset_cognito()
        clear_jwks_cache()
        # The cache lives in the database, which a SimpleTestCase may not touch (and cannot have filled).
        if 'default' in getattr(test, 'databases', ()):
            cache.clear()
        super().startTest(test)


class HairmatchTestRunner(DiscoverRunner):
    def get_resultclass(self):
        base = super().get_resultclass() or TextTestResult
        return type('CognitoResetResult', (CognitoResetMixin, base), {})
