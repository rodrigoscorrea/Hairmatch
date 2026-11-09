from unittest import TextTestResult

from django.core.cache import cache
from django.test.runner import DiscoverRunner

from hairmatch import testing_telemetry
from notifications.sns import reset_sns
from users.authentication import clear_jwks_cache
from users.cognito import reset_cognito


class CognitoResetMixin:
    """Database changes roll back between tests, so the in-memory Cognito and SNS, the key cache and the throttle counters must too."""

    def startTest(self, test):
        reset_cognito()
        reset_sns()
        clear_jwks_cache()
        testing_telemetry.clear()
        # The cache lives in the database, which a SimpleTestCase may not touch (and cannot have filled).
        if 'default' in getattr(test, 'databases', ()):
            cache.clear()
        super().startTest(test)


class HairmatchTestRunner(DiscoverRunner):
    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        # Before setup_databases: a connection opened earlier would never produce a span. In-memory exporters, not the
        # environment (TEL-05); the whole suite runs instrumented.
        testing_telemetry.install()

    def get_resultclass(self):
        base = super().get_resultclass() or TextTestResult
        return type('CognitoResetResult', (CognitoResetMixin, base), {})
