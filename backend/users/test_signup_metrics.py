import json

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from hairmatch import testing_telemetry
from users.cognito import get_cognito
from users.tests import _register_payload


class SignupStepCounterTests(testing_telemetry.TelemetryMixin, TestCase):
    """TEL-55: one count per finished step of the e-mail sign-up."""

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.fake = get_cognito().client

    def events(self):
        return sorted((attrs['step'], value) for attrs, value in self.points('hairmatch.signup.events'))

    def register(self, **overrides):
        return self.client.post(reverse('register'), data=_register_payload(**overrides))

    def post_json(self, name, body):
        return self.client.post(reverse(name), data=json.dumps(body), content_type='application/json')

    def test_an_accepted_sign_up_counts_created(self):
        self.assertEqual(self.register().status_code, 201)
        self.assertEqual(self.events(), [('created', 1)])

    def test_a_refused_sign_up_counts_nothing(self):
        self.assertEqual(self.register(role='nobody').status_code, 400)
        self.assertEqual(self.events(), [])

    def test_an_accepted_code_counts_confirmed(self):
        self.register()
        code = self.fake.confirmation_code('nova@example.com')
        response = self.post_json('email_confirmations', {'email': 'nova@example.com', 'code': code})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.events(), [('confirmed', 1), ('created', 1)])

    def test_a_wrong_code_does_not_count_confirmed(self):
        self.register()
        wrong = '000000' if self.fake.confirmation_code('nova@example.com') != '000000' else '111111'
        response = self.post_json('email_confirmations', {'email': 'nova@example.com', 'code': wrong})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.events(), [('created', 1)])

    def test_a_resent_code_counts_resent(self):
        self.register()
        self.assertEqual(self.post_json('confirmation_codes', {'email': 'nova@example.com'}).status_code, 202)
        self.assertEqual(self.events(), [('created', 1), ('resent', 1)])

    def test_a_resend_for_an_unknown_email_answers_the_same_but_counts_nothing(self):
        self.assertEqual(self.post_json('confirmation_codes', {'email': 'nobody@example.com'}).status_code, 202)
        self.assertEqual(self.events(), [])

    def test_every_429_of_the_three_routes_counts_throttled(self):
        cache.clear()  # the throttle counters live in the cache table, which other tests may have filled
        refused = []

        def call(route, response):
            if response.status_code == 429:
                refused.append(route)

        # Per-e-mail throttles allow 3 sign-ups and 3 resends an hour, and 10 confirmations; the per-IP ones allow 10 a minute.
        for _ in range(4):
            call('register', self.register())
        for _ in range(12):
            call('confirm', self.post_json('email_confirmations', {'email': 'x@example.com', 'code': '123456'}))
        for _ in range(12):
            call('resend', self.post_json('confirmation_codes', {'email': 'y@example.com'}))

        self.assertEqual({'register', 'confirm', 'resend'}, set(refused))
        self.assertEqual(dict(self.events())['throttled'], len(refused))
