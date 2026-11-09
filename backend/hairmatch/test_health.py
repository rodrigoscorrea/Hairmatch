from django.db import OperationalError, connection
from django.test import SimpleTestCase, TestCase
from unittest.mock import patch

from hairmatch import testing_telemetry
from hairmatch.problem_testing import assert_problem


class HealthTests(testing_telemetry.TelemetryMixin, TestCase):
    """TEL-34, TEL-61 to TEL-65."""

    URL = '/api/health'

    def test_the_database_answering_is_a_200_ok(self):
        """TEL-61"""
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})

    def test_a_broken_connection_is_a_503_problem_service_unavailable(self):
        """TEL-62"""
        with patch.object(connection, 'cursor', side_effect=OperationalError('connection refused: db.internal:5432')):
            response = self.client.get(self.URL)
        body = assert_problem(response, 'service-unavailable', detail='The database is not responding.')
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('db.internal', str(body))

    def test_it_answers_without_a_session_and_is_never_throttled(self):
        """TEL-63"""
        statuses = {self.client.get(self.URL).status_code for _ in range(60)}
        self.assertEqual(statuses, {200})

    def test_head_and_options_are_allowed(self):
        self.assertEqual(self.client.head(self.URL).status_code, 200)
        self.assertEqual(self.client.options(self.URL).status_code, 200)

    def test_other_methods_answer_405_method_not_allowed_with_get_in_allow(self):
        """TEL-65"""
        for method in ('post', 'put', 'patch', 'delete'):
            with self.subTest(method=method):
                response = getattr(self.client, method)(self.URL)
                assert_problem(response, 'method-not-allowed')
                self.assertEqual(response.status_code, 405)
                self.assertIn('GET', response['Allow'])

    def test_a_probe_leaves_no_span_and_no_http_metric_point(self):
        """TEL-34: not the request span, and not the SELECT 1 either."""
        self.client.get(self.URL)
        self.client.get(self.URL + '?probe=1')
        self.assertEqual([s.name for s in self.spans()], [])
        self.assertEqual(self.points('http.server.duration') + self.points('http.server.request.duration'), [])
        self.assertEqual(self.metric('http.server.request.duration'), [])

    def metric(self, name):
        return testing_telemetry.metric(name)

    def test_the_database_down_is_still_a_probe_without_spans(self):
        with patch.object(connection, 'cursor', side_effect=OperationalError('x')):
            self.client.get(self.URL)
        self.assertEqual([s.name for s in self.spans()], [])


class HealthIsIndependentTests(SimpleTestCase):
    """TEL-64: the view reads nothing but the database."""

    def test_the_module_imports_no_collector_aws_or_provider_client(self):
        import hairmatch.health as health

        source = open(health.__file__).read()
        for forbidden in ('boto3', 'requests', 'otel', 'opentelemetry', 'sns', 'cognito'):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(f'import {forbidden}', source)
                self.assertNotIn(f'from {forbidden}', source)
