import time
from unittest.mock import patch

import jwt
from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from hairmatch import testing_telemetry
from notifications.tests.helpers import make_user
from users.auth_tokens import issue_session_token
from users.cognito import CognitoUnavailable, get_cognito
from users.models import Customer


class AuthRejectionCounterTests(testing_telemetry.TelemetryMixin, TestCase):
    """TEL-54: every session the authenticator refuses adds 1, with the reason."""

    def setUp(self):
        super().setUp()
        self.user = make_user('auth@example.com', '5592900000020', 'customer')
        Customer.objects.create(user=self.user, cpf='12345678900')
        self.fake = get_cognito().client
        self.client = APIClient()
        self.url = reverse('reservation_collection')
        testing_telemetry.clear()

    def get_with(self, token):
        self.client.cookies.clear()
        if token is not None:
            self.client.cookies['jwt'] = token
        return self.client.get(self.url)

    def rejections(self):
        return sorted((attrs['reason'], value) for attrs, value in self.points('hairmatch.auth.rejections'))

    def test_no_cookie_counts_missing(self):
        self.assertEqual(self.get_with(None).status_code, 401)
        self.assertEqual(self.rejections(), [('missing', 1)])

    def test_an_expired_cognito_token_counts_expired(self):
        token = self.fake.make_access_token(self.user.cognito_sub, exp=int(time.time()) - 60)
        self.assertEqual(self.get_with(token).status_code, 401)
        self.assertEqual(self.rejections(), [('expired', 1)])

    def test_an_expired_session_token_counts_expired(self):
        payload = jwt.decode(issue_session_token(self.user), options={'verify_signature': False})
        payload['exp'] = int(time.time()) - 60
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
        self.assertEqual(self.get_with(token).status_code, 401)
        self.assertEqual(self.rejections(), [('expired', 1)])

    def test_an_expired_token_with_a_wrong_signature_is_invalid_not_expired(self):
        payload = jwt.decode(issue_session_token(self.user), options={'verify_signature': False})
        payload['exp'] = int(time.time()) - 60
        token = jwt.encode(payload, 'not-the-secret-key-at-least-32-bytes-long', algorithm='HS256')
        self.get_with(token)
        self.assertEqual(self.rejections(), [('invalid', 1)])

    def test_garbage_and_foreign_tokens_count_invalid(self):
        foreign = jwt.encode({'iss': 'someone-else', 'exp': int(time.time()) + 60}, 'k' * 32, algorithm='HS256')
        unknown_user = self.fake.make_access_token('sub-nobody')
        for token in ('not-a-jwt', foreign, unknown_user):
            self.assertEqual(self.get_with(token).status_code, 401)
        self.assertEqual(self.rejections(), [('invalid', 3)])

    def test_cognito_keys_not_fetchable_counts_unavailable(self):
        token = self.fake.make_access_token(self.user.cognito_sub)
        with patch('users.authentication._signing_key', side_effect=CognitoUnavailable('x')):
            self.assertEqual(self.get_with(token).status_code, 503)
        self.assertEqual(self.rejections(), [('unavailable', 1)])

    def test_a_valid_session_counts_nothing(self):
        token = self.fake.make_access_token(self.user.cognito_sub)
        self.assertEqual(self.get_with(token).status_code, 200)
        self.assertEqual(self.rejections(), [])

    def test_asking_whether_there_is_a_session_is_not_a_rejection(self):
        self.client.cookies.clear()
        self.assertEqual(self.client.get(reverse('session')).status_code, 200)
        self.assertEqual(self.rejections(), [])
