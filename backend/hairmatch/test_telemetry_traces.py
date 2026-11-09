import logging

from django.http import HttpResponse
from django.test import Client, TestCase, override_settings
from django.urls import path
from opentelemetry import trace
from opentelemetry.trace import SpanKind

from hairmatch import testing_telemetry
from hairmatch.logs import JsonFormatter, TraceContextFilter

ROUTE = 'api/hairdressers/<int:hairdresser_id>/gallery-photos'
GALLERY = '/api/hairdressers/987654/gallery-photos'
TRACE_ID = '0af7651916cd43dd8448eb211c80319c'
PARENT_ID = 'b7ad6b7169203331'
FORBIDDEN = {'url.query', 'url.full', 'url.path', 'http.url', 'http.target', 'client.address', 'enduser.id'}


class RequestSpanTests(testing_telemetry.TelemetryMixin, TestCase):
    """TEL-16, TEL-17, TEL-20, TEL-21, TEL-35, TEL-82, TEL-83."""

    def get(self, path=GALLERY, **headers):
        return Client().get(path, **headers)

    def test_request_creates_a_server_span_named_and_routed_by_the_template(self):
        self.get(GALLERY + '?email=ana@example.com')
        server = self.span(kind=SpanKind.SERVER)
        self.assertEqual(server.attributes['http.route'], ROUTE)
        self.assertEqual(server.name, f'GET {ROUTE}')
        self.assertEqual(server.attributes['http.response.status_code'], 404)
        everything = repr(dict(server.attributes)) + server.name
        self.assertNotIn('987654', everything)
        self.assertNotIn('ana@example.com', everything)

    def test_server_span_has_none_of_the_forbidden_attributes(self):
        """TEL-47."""
        self.get(GALLERY + '?email=ana@example.com', HTTP_COOKIE='jwt=abc', HTTP_AUTHORIZATION='Bearer abc')
        server = self.span(kind=SpanKind.SERVER)
        self.assertEqual(FORBIDDEN & set(server.attributes), set())
        self.assertEqual([k for k in server.attributes if k.startswith('http.request.header.')], [])

    def test_query_is_a_child_client_span_with_the_statement_and_without_the_values(self):
        self.get(GALLERY)
        server = self.span(kind=SpanKind.SERVER)
        queries = [s for s in self.spans() if s.kind == SpanKind.CLIENT and s.attributes.get('db.system') == 'postgresql']
        self.assertTrue(queries)
        for query in queries:
            self.assertEqual(query.parent.span_id, server.context.span_id)
            self.assertEqual(query.context.trace_id, server.context.trace_id)
        statements = ' '.join(q.attributes['db.statement'] for q in queries)
        self.assertIn('users_hairdresser', statements)
        self.assertIn('%s', statements)
        self.assertNotIn('987654', statements)

    def test_valid_traceparent_gives_the_trace_id_and_the_parent(self):
        self.get(HTTP_TRACEPARENT=f'00-{TRACE_ID}-{PARENT_ID}-01')
        server = self.span(kind=SpanKind.SERVER)
        self.assertEqual(format(server.context.trace_id, '032x'), TRACE_ID)
        self.assertEqual(format(server.parent.span_id, '016x'), PARENT_ID)

    def test_invalid_traceparent_is_ignored_and_the_answer_is_the_same(self):
        baseline = self.get()
        for header in (
            'garbage', f'00-{TRACE_ID}-{PARENT_ID}', f'00-{"0" * 32}-{PARENT_ID}-01',
            f'00-{TRACE_ID}-{"0" * 16}-01', f'ff-{TRACE_ID}-{PARENT_ID}-01', f'00-{TRACE_ID.upper()}-{PARENT_ID}-01',
        ):
            with self.subTest(header=header):
                testing_telemetry.clear()
                response = self.get(HTTP_TRACEPARENT=header)
                self.assertEqual((response.status_code, response.content), (baseline.status_code, baseline.content))
                server = self.span(kind=SpanKind.SERVER)
                self.assertNotEqual(format(server.context.trace_id, '032x'), TRACE_ID)
                self.assertIsNone(server.parent)

    def test_request_without_traceparent_is_sampled_and_exported(self):
        """TEL-35."""
        self.get()
        self.assertTrue(self.span(kind=SpanKind.SERVER).context.trace_flags.sampled)

    def test_flag_00_is_not_exported_and_the_answer_is_normal(self):
        """TEL-82."""
        baseline = self.get()
        testing_telemetry.clear()
        response = self.get(HTTP_TRACEPARENT=f'00-{TRACE_ID}-{PARENT_ID}-00')
        self.assertEqual((response.status_code, response.content), (baseline.status_code, baseline.content))
        self.assertEqual(self.spans(), [])

    def test_request_outside_api_follows_the_same_rules(self):
        """TEL-83."""
        Client().get('/admin/login/?next=ana@example.com', HTTP_COOKIE='sessionid=abc')
        server = self.span(kind=SpanKind.SERVER)
        self.assertEqual(FORBIDDEN & set(server.attributes), set())
        self.assertNotIn('ana@example.com', repr(dict(server.attributes)) + server.name)

    def test_preflight_options_span_has_no_raw_path(self):
        Client().options(
            '/api/postal-codes/69000000', HTTP_ORIGIN='http://localhost:8081', HTTP_ACCESS_CONTROL_REQUEST_METHOD='GET',
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS='traceparent',
        )
        server = self.span(kind=SpanKind.SERVER)
        self.assertNotIn('69000000', repr(dict(server.attributes)) + server.name)


class RequestMetricTests(testing_telemetry.TelemetryMixin, TestCase):
    """TEL-32, TEL-33."""

    def test_duration_histogram_is_in_seconds_with_the_route_label(self):
        Client().get(GALLERY)
        (histogram,) = [m for m in testing_telemetry.metric('http.server.request.duration')]
        self.assertEqual(histogram.unit, 's')
        (point,) = histogram.data.data_points
        self.assertEqual(point.attributes['http.route'], ROUTE)
        self.assertEqual(point.attributes['http.response.status_code'], 404)
        self.assertEqual(point.count, 1)
        self.assertEqual(histogram.name, 'http.server.request.duration')

    def test_the_point_carries_an_exemplar_with_the_trace_id_of_the_request_span(self):
        Client().get(GALLERY)
        server = self.span(kind=SpanKind.SERVER)
        (histogram,) = testing_telemetry.metric('http.server.request.duration')
        (point,) = histogram.data.data_points
        self.assertEqual([e.trace_id for e in point.exemplars], [server.context.trace_id])
        self.assertEqual([e.span_id for e in point.exemplars], [server.context.span_id])


def probe(request):
    logging.getLogger('probe').warning('inside the view')
    return HttpResponse('ok')


# A route of its own for the log test: the "Not Found" line of Django is written after the request span has ended.
urlpatterns = [path('api/log-probe', probe)]


@override_settings(ROOT_URLCONF='hairmatch.test_telemetry_traces')
class LogCorrelationTests(testing_telemetry.TelemetryMixin, TestCase):
    """TEL-37, TEL-39: a log written during a request carries the trace and span of the request, in stdout and in OTLP."""

    def test_log_during_a_request_has_the_trace_and_span_of_the_request(self):
        Client().get('/api/log-probe')
        server = self.span(kind=SpanKind.SERVER)
        (record,) = [r for r in self.log_records() if r.body == 'inside the view']
        self.assertEqual(record.trace_id, server.context.trace_id)
        self.assertEqual(record.span_id, server.context.span_id)

    def test_stdout_line_has_the_same_ids_as_the_active_span(self):
        import io
        import json

        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JsonFormatter())
        handler.addFilter(TraceContextFilter())
        logger = logging.getLogger('test.stdout.ids')
        logger.handlers, logger.propagate = [handler], False
        with trace.get_tracer('t').start_as_current_span('request') as span:
            logger.warning('inside')
        line = json.loads(stream.getvalue())
        self.assertEqual(line['trace_id'], format(span.get_span_context().trace_id, '032x'))
        self.assertEqual(line['span_id'], format(span.get_span_context().span_id, '016x'))
