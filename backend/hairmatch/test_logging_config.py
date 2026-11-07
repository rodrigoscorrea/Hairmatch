import json
import os
import subprocess
import sys

from django.conf import settings
from django.test import Client, SimpleTestCase


def run_python(code):
    """Runs `code` in a fresh interpreter with the real settings (no test runner) and returns the stdout lines."""
    env = {**os.environ, 'DJANGO_SETTINGS_MODULE': 'hairmatch.settings'}
    env.pop('OTEL_EXPORTER_OTLP_ENDPOINT', None)
    done = subprocess.run(
        [sys.executable, '-W', 'ignore', '-c', 'import django; django.setup()\n' + code],
        cwd=settings.BASE_DIR, env=env, capture_output=True, text=True, timeout=120, check=True,
    )
    return [line for line in done.stdout.splitlines() if line.startswith('{')]


class LoggingConfigTests(SimpleTestCase):
    """TEL-14, TEL-36, TEL-43, TEL-46: the real LOGGING, read in a fresh interpreter."""

    def test_application_log_is_a_redacted_json_line_on_stdout(self):
        (line,) = run_python("import logging; logging.getLogger('app').warning('reset for %s', 'ana@example.com')")
        record = json.loads(line)
        self.assertEqual(
            (record['level'], record['name'], record['message']), ('WARNING', 'app', 'reset for [email]')
        )
        self.assertIn('ts', record)

    def test_info_is_logged_and_debug_is_not(self):
        lines = run_python("import logging; l = logging.getLogger('app'); l.debug('d'); l.info('i')")
        self.assertEqual([json.loads(line)['message'] for line in lines], ['i'])

    def test_django_server_access_log_has_no_query_string(self):
        (line,) = run_python(
            "import logging; logging.getLogger('django.server').info('\"%s\" %s %s', 'GET /api/search?q=ana HTTP/1.1', '200', '9')"
        )
        record = json.loads(line)
        self.assertEqual(record['message'], '"GET /api/search HTTP/1.1" 200 9')
        self.assertEqual(record['name'], 'django.server')

    def test_django_logger_prints_once_as_json_not_as_text(self):
        lines = run_python("import logging; logging.getLogger('django.request').warning('Not Found: /x')")
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])['message'], 'Not Found: /x')

    def test_opentelemetry_logger_goes_to_stdout_only_and_never_to_the_root_handlers(self):
        lines = run_python(
            "import logging\n"
            "assert logging.getLogger('opentelemetry').propagate is False\n"
            "assert logging.getLogger('urllib3').propagate is False\n"
            "logging.getLogger('opentelemetry.sdk.trace.export').error('export failed for a@b.co')"
        )
        self.assertEqual([json.loads(line)['message'] for line in lines], ['export failed for [email]'])


class CorsTraceparentTests(SimpleTestCase):
    """TEL-75: the preflight that carries `traceparent` is accepted."""

    def test_traceparent_is_an_allowed_header(self):
        self.assertIn('traceparent', settings.CORS_ALLOW_HEADERS)

    def test_preflight_asking_for_traceparent_is_allowed_for_the_web_origin(self):
        response = Client().options(
            '/api/postal-codes/69000000',
            HTTP_ORIGIN='http://localhost:8081',
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='GET',
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS='traceparent',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('traceparent', response['Access-Control-Allow-Headers'])
        self.assertEqual(response['Access-Control-Allow-Origin'], 'http://localhost:8081')

    def test_a_header_outside_the_list_is_still_refused(self):
        response = Client().options(
            '/api/postal-codes/69000000',
            HTTP_ORIGIN='http://localhost:8081',
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='GET',
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS='x-unlisted',
        )
        self.assertNotIn('x-unlisted', response.get('Access-Control-Allow-Headers', ''))
