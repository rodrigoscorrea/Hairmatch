"""
The backend does not depend on the Collector (#194, TEL-09, TEL-10, TEL-11, TEL-15, TEL-84).

Each mode runs a real `runserver --noreload` in a process of its own: the providers of OpenTelemetry and the middleware
of Django cannot be undone inside the process of the test runner. The server is reached over HTTP on loopback.
"""
import json
import os
import signal
import socket
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from django.conf import settings
from django.test import SimpleTestCase

# Faster batches than the production ones, so a few seconds of traffic exercise every exporter.
FAST_BATCHES = {'OTEL_BSP_SCHEDULE_DELAY': '300', 'OTEL_BLRP_SCHEDULE_DELAY': '300'}
MODES = {
    'refused': 'http://127.0.0.1:1',
    'unresolvable': 'http://collector.invalid:4318',
    'silent': 'http://192.0.2.1:4318',  # TEST-NET-1: nobody answers
}
ROUTES = (
    ('GET', '/api/nope', {}),
    ('GET', '/api/auth/session', {}),
    ('GET', '/api/health', {}),
    ('OPTIONS', '/api/postal-codes/69000000', {
        'Origin': 'http://localhost:8081', 'Access-Control-Request-Method': 'GET', 'Access-Control-Request-Headers': 'traceparent',
    }),
)
SERIES = 50
SERIES_ROUTE = '/api/nope'  # instrumented, and logs one warning per request
P95_MARGIN_SECONDS = 0.050
SHUTDOWN_LIMIT_SECONDS = 5.0


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


class Server:
    """`runserver --noreload` on a free port; the output goes to a file so a long run cannot fill a pipe."""

    def __init__(self, endpoint=None):
        self.port = free_port()
        self.base = f'http://127.0.0.1:{self.port}'
        env = {k: v for k, v in os.environ.items() if not k.startswith('OTEL_')}
        env.update({'DJANGO_SETTINGS_MODULE': 'hairmatch.settings', **FAST_BATCHES})
        if endpoint:
            env['OTEL_EXPORTER_OTLP_ENDPOINT'] = endpoint
        self.output = tempfile.NamedTemporaryFile('w+', suffix='.log', delete=False)
        self.process = subprocess.Popen(
            [sys.executable, '-W', 'ignore', 'manage.py', 'runserver', '--noreload', f'127.0.0.1:{self.port}'],
            cwd=settings.BASE_DIR, env=env, stdout=self.output, stderr=subprocess.STDOUT,
        )

    def __enter__(self):
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise AssertionError(f'the server died:\n{self.lines_raw()}')
            try:
                if self.request('GET', '/api/health')[0] == 200:
                    return self
            except OSError:
                time.sleep(0.2)
        raise AssertionError(f'the server did not start:\n{self.lines_raw()}')

    def __exit__(self, *exc):
        self.stop()
        os.unlink(self.output.name)

    def request(self, method, path, headers=None):
        """(status, body, seconds)."""
        request = urllib.request.Request(self.base + path, method=method, headers=headers or {})
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                status, body = response.status, response.read()
        except urllib.error.HTTPError as error:
            status, body = error.code, error.read()
        return status, body, time.perf_counter() - started

    def stop(self):
        """SIGTERM and the seconds until the process is gone."""
        if self.process.poll() is not None:
            return 0.0
        started = time.monotonic()
        self.process.send_signal(signal.SIGTERM)
        try:
            self.process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
        return time.monotonic() - started

    def lines_raw(self):
        self.output.flush()
        with open(self.output.name) as handle:
            return handle.read()

    def logs(self):
        found = []
        for line in self.lines_raw().splitlines():
            if line.startswith('{'):
                try:
                    found.append(json.loads(line))
                except ValueError:
                    pass
        return found

    def series(self):
        durations = sorted(self.request('GET', SERIES_ROUTE)[2] for _ in range(SERIES))
        return durations[int(0.95 * SERIES) - 1]  # the 48th of 50


def covered_routes(server):
    return [server.request(method, path, headers)[:2] for method, path, headers in ROUTES]


def export_error_lines(logs):
    """The warning and error lines of the SDK exporters, by signal."""
    by_signal = {}
    for record in logs:
        name = record.get('name', '')
        if name.startswith('opentelemetry') and record.get('level') in ('WARNING', 'ERROR'):
            signal_name = next((s for s, hint in (('traces', 'trace'), ('metrics', 'metric'), ('logs', 'log')) if hint in name), name)
            by_signal.setdefault(signal_name, []).append(record)
    return by_signal


class CollectorDownTests(SimpleTestCase):
    """TEL-09, TEL-10, TEL-11, TEL-15, one server per mode, compared with a server that has no Collector configured."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with Server() as baseline:
            cls.expected = covered_routes(baseline)
            cls.baseline_p95 = baseline.series()
        cls.runs = {}
        for mode, endpoint in MODES.items():
            with Server(endpoint) as server:
                answers = covered_routes(server)
                p95 = server.series()
                time.sleep(3)  # long enough for every batch exporter to try and fail
                logs_before_stop = server.logs()
                stopped_in = server.stop()
                cls.runs[mode] = {'answers': answers, 'p95': p95, 'logs': logs_before_stop, 'stopped_in': stopped_in}

    def test_every_covered_route_answers_as_it_does_without_telemetry(self):
        """TEL-09"""
        self.assertEqual([status for status, _ in self.expected], [404, 200, 200, 200])
        for mode, run in self.runs.items():
            with self.subTest(mode=mode):
                self.assertEqual(run['answers'], self.expected)

    def test_the_p95_of_fifty_requests_is_within_50_ms_of_the_baseline(self):
        """TEL-10"""
        for mode, run in self.runs.items():
            with self.subTest(mode=mode, baseline=self.baseline_p95, p95=run['p95']):
                self.assertLessEqual(run['p95'], self.baseline_p95 + P95_MARGIN_SECONDS)

    def test_the_server_ends_within_five_seconds_of_a_sigterm(self):
        """TEL-11"""
        for mode, run in self.runs.items():
            with self.subTest(mode=mode, seconds=run['stopped_in']):
                self.assertLess(run['stopped_in'], SHUTDOWN_LIMIT_SECONDS)

    def test_at_most_one_export_error_line_per_signal(self):
        """TEL-15: and the failure is not silent, either: traces and logs report it once."""
        for mode, run in self.runs.items():
            with self.subTest(mode=mode):
                by_signal = export_error_lines(run['logs'])
                for signal_name, lines in by_signal.items():
                    self.assertLessEqual(len(lines), 1, (signal_name, [line['message'][:120] for line in lines]))
                self.assertTrue({'traces', 'logs'} <= set(by_signal), sorted(by_signal))

    def test_the_series_is_made_of_requests_that_log_one_line_each(self):
        """TEL-10 premise: the route of the series emits a log per request."""
        for mode, run in self.runs.items():
            with self.subTest(mode=mode):
                warnings = [r for r in run['logs'] if r.get('name') == 'django.request' and SERIES_ROUTE in r.get('message', '')]
                self.assertGreaterEqual(len(warnings), SERIES)


class FakeCollector:
    """Accepts the OTLP/HTTP posts and keeps their bodies by path."""

    def __init__(self, port):
        received = self.received = {'/v1/traces': [], '/v1/logs': [], '/v1/metrics': []}

        class Handler(BaseHTTPRequestHandler):
            def do_POST(handler):
                body = handler.rfile.read(int(handler.headers.get('Content-Length', 0)))
                received.setdefault(handler.path, []).append(body)
                handler.send_response(200)
                handler.send_header('Content-Type', 'application/x-protobuf')
                handler.send_header('Content-Length', '0')
                handler.end_headers()

            def log_message(handler, *args):
                pass

        self.httpd = ThreadingHTTPServer(('127.0.0.1', port), Handler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()

    def wait_for(self, path, needle, seconds):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if any(needle in body for body in self.received[path]):
                return True
            time.sleep(0.2)
        return False


class CollectorBackTests(SimpleTestCase):
    """TEL-84: a Collector that comes back receives what happens after, without restarting the backend."""

    def test_new_signals_are_exported_once_the_collector_returns(self):
        port = free_port()
        before, after = '0af7651916cd43dd8448eb211c80319c', 'b9c7c989f97918e1c4f7f1a2d7ac0b1e'
        with Server(f'http://127.0.0.1:{port}') as server:
            server.request('GET', '/api/nope-before', {'traceparent': f'00-{before}-b7ad6b7169203331-01'})
            time.sleep(2.5)  # the exporters try and fail while nobody listens
            collector = FakeCollector(port)
            self.addCleanup(collector.close)
            server.request('GET', '/api/nope-after', {'traceparent': f'00-{after}-b7ad6b7169203331-01'})
            self.assertTrue(collector.wait_for('/v1/traces', bytes.fromhex(after), 20), 'no span of the new request reached the Collector')
            # Django logs the 404 after the span of the request has ended, so the log carries the path and not the trace id.
            self.assertTrue(collector.wait_for('/v1/logs', b'Not Found: /api/nope-after', 20), 'no log of the new request reached the Collector')
            deadline = time.monotonic() + 30
            while not collector.received['/v1/metrics'] and time.monotonic() < deadline:
                time.sleep(0.3)
            self.assertTrue(collector.received['/v1/metrics'], 'no metrics reached the Collector')
            self.assertLess(server.stop(), SHUTDOWN_LIMIT_SECONDS)

        self.assert_collector_calls_are_not_traced(collector, port)

    def assert_collector_calls_are_not_traced(self, collector, port):
        """The exporter's own POSTs to the Collector are not spans (the requests instrumentation leaves that host out)."""
        from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest

        names = []
        for body in collector.received['/v1/traces']:
            request = ExportTraceServiceRequest()
            request.ParseFromString(body)
            for resource_spans in request.resource_spans:
                for scope_spans in resource_spans.scope_spans:
                    for span in scope_spans.spans:
                        names.append(span.name)
                        for attribute in span.attributes:
                            self.assertNotEqual(attribute.value.string_value, '127.0.0.1')
        self.assertTrue(names)
        self.assertNotIn('POST', names)
