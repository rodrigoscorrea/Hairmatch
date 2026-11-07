import os
import threading
import time
from unittest import mock

from django.test import SimpleTestCase
from opentelemetry.context import Context
from opentelemetry.sdk._logs.export import InMemoryLogRecordExporter
from opentelemetry.sdk.metrics.export import MetricExporter, MetricExportResult
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags, set_span_in_context
import logging

from hairmatch import otel
from hairmatch.process_testing import run_python

IMPORT_WSGI_WITH_SPY = '''
import json, socket, sys, threading
connects = []
real_connect = socket.socket.connect
def spy(self, *args, **kwargs):
    connects.append(repr(args))
    return real_connect(self, *args, **kwargs)
socket.socket.connect = spy
threads_before = threading.active_count()
import hairmatch.wsgi
from opentelemetry import trace, metrics, _logs
import logging
print('REPORT ' + json.dumps({
    'tracer': type(trace.get_tracer_provider()).__name__,
    'meter': type(metrics.get_meter_provider()).__name__,
    'logger': type(_logs.get_logger_provider()).__name__,
    'sdk_modules': sorted(m for m in sys.modules if m.startswith('opentelemetry.sdk')),
    'otel_module': 'hairmatch.otel' in sys.modules,
    'connects': connects,
    'new_threads': threading.active_count() - threads_before,
    'root_handlers': [type(h).__name__ for h in logging.getLogger().handlers],
}))
'''

ENABLED_REPORT = '''
import json, logging
import hairmatch.wsgi
from hairmatch import telemetry
from django.conf import settings
from opentelemetry import trace, metrics, _logs
again = telemetry.init_telemetry()
again_twice = telemetry.init_telemetry()
tp = trace.get_tracer_provider()
processors = tp._active_span_processor._span_processors
batch = processors[0]._inner._batch_processor
mp = metrics.get_meter_provider()
reader = next(iter(mp._all_metric_readers))
lp = _logs.get_logger_provider()
log_batch = lp._multi_log_record_processor._log_record_processors[0]._batch_processor
print('REPORT ' + json.dumps({
    'enabled_again': [again, again_twice],
    'tracer': type(tp).__name__, 'meter': type(mp).__name__, 'logger': type(lp).__name__,
    'span_processors': [type(p).__name__ for p in processors],
    'sampler': tp.sampler.get_description(),
    'span_queue': batch._max_queue_size, 'span_export_timeout_ms': batch._export_timeout_millis,
    'span_exporter_timeout_s': batch._exporter._client._timeout,
    'metric_reader': type(reader).__name__,
    'metric_interval_ms': reader._export_interval_millis, 'metric_timeout_ms': reader._export_timeout_millis,
    'metric_exporter_timeout_s': reader._exporter._client._timeout,
    'log_queue': log_batch._max_queue_size, 'log_export_timeout_ms': log_batch._export_timeout_millis,
    'log_exporter_timeout_s': log_batch._exporter._client._timeout,
    'otlp_handlers': sum(type(h).__name__ == 'OtlpLogHandler' for h in logging.getLogger().handlers),
    'django_middleware': [m for m in settings.MIDDLEWARE if 'opentelemetry' in m],
    'semconv': __import__('os').environ.get('OTEL_SEMCONV_STABILITY_OPT_IN'),
}))
'''


class DisabledTests(SimpleTestCase):
    """TEL-01, TEL-02: without the endpoint the providers stay no-ops and nothing opens, starts or logs."""

    def check(self, env):
        report, logs, _ = run_python(IMPORT_WSGI_WITH_SPY, env=env)
        self.assertEqual(report['tracer'], 'ProxyTracerProvider')
        self.assertEqual(report['meter'], '_ProxyMeterProvider')
        self.assertEqual(report['logger'], 'ProxyLoggerProvider')
        self.assertEqual(report['sdk_modules'], [])
        self.assertFalse(report['otel_module'])
        self.assertEqual(report['connects'], [])
        self.assertEqual(report['new_threads'], 0)
        self.assertNotIn('OtlpLogHandler', report['root_handlers'])
        self.assertEqual(logs, [])

    def test_endpoint_absent(self):
        self.check({})

    def test_endpoint_empty(self):
        self.check({'OTEL_EXPORTER_OTLP_ENDPOINT': ''})

    def test_endpoint_blank(self):
        self.check({'OTEL_EXPORTER_OTLP_ENDPOINT': '   '})


class EnabledTests(SimpleTestCase):
    """TEL-04 and the configuration of TEL-06, TEL-07, TEL-08, TEL-35, TEL-32."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.report, _, _ = run_python(ENABLED_REPORT, env={'OTEL_EXPORTER_OTLP_ENDPOINT': 'http://127.0.0.1:1'})

    def test_providers_are_the_sdk_ones(self):
        self.assertEqual(
            (self.report['tracer'], self.report['meter'], self.report['logger']),
            ('TracerProvider', 'MeterProvider', 'LoggerProvider'),
        )

    def test_calling_the_entry_point_again_changes_nothing(self):
        """TEL-04: the first call in `hairmatch.wsgi` already started it; later calls are ignored."""
        self.assertEqual(self.report['enabled_again'], [True, True])
        self.assertEqual(self.report['span_processors'], ['SanitizingSpanProcessor'])
        self.assertEqual(self.report['otlp_handlers'], 1)
        self.assertEqual(len(self.report['django_middleware']), 1)

    def test_export_is_batched_in_the_background(self):
        """TEL-06."""
        self.assertEqual(self.report['metric_reader'], 'PeriodicExportingMetricReader')
        self.assertGreater(self.report['span_queue'], 0)

    def test_each_export_gives_up_after_two_seconds(self):
        """TEL-07: the exporter deadline and the processor deadline."""
        self.assertEqual(self.report['span_exporter_timeout_s'], 2)
        self.assertEqual(self.report['metric_exporter_timeout_s'], 2)
        self.assertEqual(self.report['log_exporter_timeout_s'], 2)
        self.assertEqual(self.report['span_export_timeout_ms'], 2000)
        self.assertEqual(self.report['metric_timeout_ms'], 2000)
        self.assertEqual(self.report['log_export_timeout_ms'], 2000)

    def test_queues_hold_2048_items_and_metrics_go_out_every_15_seconds(self):
        """TEL-08 and the limits of the spec."""
        self.assertEqual((self.report['span_queue'], self.report['log_queue']), (2048, 2048))
        self.assertEqual(self.report['metric_interval_ms'], 15000)

    def test_sampling_follows_the_parent_and_keeps_everything_else(self):
        """TEL-35."""
        self.assertIn('ParentBased{root:AlwaysOnSampler', self.report['sampler'])
        self.assertIn('remoteParentNotSampled:AlwaysOffSampler', self.report['sampler'])

    def test_stable_http_conventions_are_selected_for_the_duration_metric(self):
        """TEL-32."""
        self.assertEqual(self.report['semconv'], 'http')


class FailureTests(SimpleTestCase):
    """TEL-03: a failure to start logs one WARNING with the exception type and the app goes on."""

    SCRIPT = '''
import json
{prelude}
import hairmatch.wsgi
from hairmatch import telemetry
from django.test import Client
telemetry.init_telemetry()
telemetry.init_telemetry()
response = Client().get('/api/no-such-route', HTTP_HOST='localhost')
from opentelemetry import trace
print('REPORT ' + json.dumps({{'status': response.status_code, 'tracer': type(trace.get_tracer_provider()).__name__}}))
'''
    ENV = {'OTEL_EXPORTER_OTLP_ENDPOINT': 'http://127.0.0.1:1'}

    def check(self, prelude, expected_type):
        report, logs, _ = run_python(self.SCRIPT.format(prelude=prelude), env=self.ENV)
        warnings = [line for line in logs if line['name'] == 'hairmatch.telemetry']
        self.assertEqual(len(warnings), 1, logs)
        self.assertEqual(warnings[0]['message'], f'telemetry disabled, the SDK failed to start: {expected_type}')
        self.assertEqual(report['status'], 404)
        self.assertEqual(report['tracer'], 'ProxyTracerProvider')

    def test_exception_while_starting_logs_the_type_and_never_the_message(self):
        self.check(
            "from hairmatch import otel\n"
            "def boom(environ=None):\n    raise RuntimeError('secret ana@example.com')\n"
            "otel.start = boom",
            'RuntimeError',
        )

    def test_message_of_the_exception_is_not_in_the_log(self):
        _, logs, _ = run_python(
            self.SCRIPT.format(prelude=(
                "from hairmatch import otel\n"
                "def boom(environ=None):\n    raise RuntimeError('secret ana@example.com')\n"
                "otel.start = boom"
            )), env=self.ENV,
        )
        self.assertNotIn('secret', str(logs))
        self.assertNotIn('ana@example.com', str(logs))

    def test_import_error_of_the_sdk_is_a_start_failure_too(self):
        self.check("import sys\nsys.modules['opentelemetry.sdk.trace'] = None", 'ModuleNotFoundError')


class ManagementCommandsTests(SimpleTestCase):
    """TEL-05: `manage.py` commands and the test runner do not start the telemetry, even with the endpoint set."""

    ENV = {'OTEL_EXPORTER_OTLP_ENDPOINT': 'http://127.0.0.1:1'}
    REPORT = '''
import json, sys
from opentelemetry import trace
print('REPORT ' + json.dumps({
    'tracer': type(trace.get_tracer_provider()).__name__,
    'wsgi': 'hairmatch.wsgi' in sys.modules,
    'sdk': sorted(m for m in sys.modules if m.startswith('opentelemetry.sdk')),
}))
'''

    def test_manage_py_check_does_not_start_it(self):
        report, _, _ = run_python(
            "import runpy, sys\nsys.argv = ['manage.py', 'check']\n"
            "try:\n    runpy.run_path('manage.py', run_name='__main__')\nexcept SystemExit:\n    pass\n" + self.REPORT,
            env=self.ENV,
        )
        self.assertEqual(report, {'tracer': 'ProxyTracerProvider', 'wsgi': False, 'sdk': []})

    def test_importing_the_test_runner_and_the_settings_does_not_start_it(self):
        report, _, _ = run_python(
            "import django; django.setup()\nfrom hairmatch import test_runner\n" + self.REPORT, env=self.ENV,
        )
        self.assertEqual(report, {'tracer': 'ProxyTracerProvider', 'wsgi': False, 'sdk': []})

    def test_importing_the_wsgi_module_is_what_starts_it(self):
        report, _, _ = run_python(
            "import hairmatch.wsgi\n" + self.REPORT, env=self.ENV,
        )
        self.assertEqual(report['tracer'], 'TracerProvider')
        self.assertTrue(report['wsgi'])


class RecordingSpanExporter(SpanExporter):
    def __init__(self):
        self.threads, self.spans = [], []

    def export(self, spans):
        self.threads.append(threading.current_thread())
        self.spans.extend(spans)
        return SpanExportResult.SUCCESS

    def shutdown(self):
        pass


class RecordingMetricExporter(MetricExporter):
    def __init__(self):
        super().__init__()
        self.threads, self.data = [], []

    def export(self, metrics_data, timeout_millis=10000, **kwargs):
        self.threads.append(threading.current_thread())
        self.data.append(metrics_data)
        return MetricExportResult.SUCCESS

    def force_flush(self, timeout_millis=10000):
        return True

    def shutdown(self, timeout_millis=30000, **kwargs):
        pass


class BlockingSpanExporter(SpanExporter):
    def __init__(self):
        self.release = threading.Event()
        self.spans = []

    def export(self, spans):
        self.release.wait(30)
        self.spans.extend(spans)
        return SpanExportResult.SUCCESS

    def shutdown(self):
        self.release.set()


def wait_for(condition, seconds=5):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.02)
    return False


class PipelineTests(SimpleTestCase):
    """The providers behind `start`, built with exporters that record or block."""

    def setUp(self):
        patcher = mock.patch.dict(os.environ, {'OTEL_BSP_SCHEDULE_DELAY': '30', 'OTEL_BLRP_SCHEDULE_DELAY': '30'})
        patcher.start()
        self.addCleanup(patcher.stop)

    def build(self, span_exporter=None, metric_exporter=None, log_exporter=None):
        pipeline = otel.Pipeline(
            otel.build_resource({'OTEL_RESOURCE_ATTRIBUTES': 'service.version=9.9'}),
            span_exporter or RecordingSpanExporter(),
            metric_exporter or RecordingMetricExporter(),
            log_exporter or InMemoryLogRecordExporter(),
            metric_interval_millis=40,
        )
        self.addCleanup(pipeline.shutdown, 2)
        return pipeline

    def test_spans_are_exported_from_a_thread_that_is_not_the_caller(self):
        """TEL-06."""
        exporter = RecordingSpanExporter()
        pipeline = self.build(span_exporter=exporter)
        with pipeline.tracer_provider.get_tracer('t').start_as_current_span('work'):
            pass
        self.assertTrue(wait_for(lambda: exporter.spans))
        self.assertNotIn(threading.current_thread(), exporter.threads)

    def test_metrics_are_exported_from_a_thread_that_is_not_the_caller(self):
        """TEL-06."""
        exporter = RecordingMetricExporter()
        pipeline = self.build(metric_exporter=exporter)
        pipeline.meter_provider.get_meter('t').create_counter('c').add(1)
        self.assertTrue(wait_for(lambda: exporter.data))
        self.assertNotIn(threading.current_thread(), exporter.threads)

    def test_logs_are_exported_from_a_thread_that_is_not_the_caller(self):
        """TEL-06."""
        exporter = InMemoryLogRecordExporter()
        pipeline = self.build(log_exporter=exporter)
        logger = self.logger_for(pipeline)
        logger.info('hello')
        self.assertTrue(wait_for(lambda: exporter.get_finished_logs()))

    def logger_for(self, pipeline):
        logger = logging.getLogger(f'test.pipeline.{id(pipeline)}')
        logger.propagate = False
        logger.setLevel(logging.DEBUG)
        handler = pipeline.log_handler()
        logger.addHandler(handler)
        self.addCleanup(logger.removeHandler, handler)
        return logger

    def test_full_queue_drops_new_spans_without_blocking_the_producer(self):
        """TEL-08."""
        exporter = BlockingSpanExporter()
        pipeline = self.build(span_exporter=exporter)
        tracer = pipeline.tracer_provider.get_tracer('t')
        started = time.monotonic()
        for _ in range(5000):
            tracer.start_span('s').end()
        elapsed = time.monotonic() - started
        self.assertLess(elapsed, 3.0)
        exporter.release.set()
        wait_for(lambda: len(exporter.spans) >= 2048)
        time.sleep(0.3)
        # One batch of 512 was already in the exporter, and the queue held 2048.
        self.assertLessEqual(len(exporter.spans), 2048 + 512)
        self.assertLess(len(exporter.spans), 5000)

    def test_trace_without_a_parent_is_exported(self):
        """TEL-35."""
        exporter = RecordingSpanExporter()
        pipeline = self.build(span_exporter=exporter)
        pipeline.tracer_provider.get_tracer('t').start_span('root').end()
        self.assertTrue(wait_for(lambda: len(exporter.spans) == 1))

    def parent(self, flags):
        context = SpanContext(0x0AF7651916CD43DD8448EB211C80319C, 0xB7AD6B7169203331, is_remote=True, trace_flags=TraceFlags(flags))
        return set_span_in_context(NonRecordingSpan(context), Context())

    def test_sampled_remote_parent_is_exported_under_the_received_trace_id(self):
        """TEL-35."""
        exporter = RecordingSpanExporter()
        pipeline = self.build(span_exporter=exporter)
        pipeline.tracer_provider.get_tracer('t').start_span('child', context=self.parent(1)).end()
        self.assertTrue(wait_for(lambda: len(exporter.spans) == 1))
        self.assertEqual(exporter.spans[0].context.trace_id, 0x0AF7651916CD43DD8448EB211C80319C)

    def test_remote_parent_with_flag_00_is_not_exported_and_the_decision_is_propagated(self):
        """TEL-82."""
        exporter = RecordingSpanExporter()
        pipeline = self.build(span_exporter=exporter)
        span = pipeline.tracer_provider.get_tracer('t').start_span('child', context=self.parent(0))
        context = span.get_span_context()
        span.end()
        time.sleep(0.3)
        self.assertEqual(exporter.spans, [])
        self.assertEqual(context.trace_id, 0x0AF7651916CD43DD8448EB211C80319C)
        self.assertFalse(context.trace_flags.sampled)

    def test_every_signal_carries_the_same_resource(self):
        """TEL-29, TEL-30, TEL-31."""
        spans, metrics_exporter, logs = RecordingSpanExporter(), RecordingMetricExporter(), InMemoryLogRecordExporter()
        pipeline = self.build(spans, metrics_exporter, logs)
        with pipeline.tracer_provider.get_tracer('t').start_as_current_span('work'):
            pass
        pipeline.meter_provider.get_meter('t').create_counter('c').add(1)
        self.logger_for(pipeline).info('hello')
        self.assertTrue(wait_for(lambda: spans.spans and metrics_exporter.data and logs.get_finished_logs()))
        resources = {
            'span': dict(spans.spans[0].resource.attributes),
            'metric': dict(metrics_exporter.data[0].resource_metrics[0].resource.attributes),
            'log': dict(logs.get_finished_logs()[0].resource.attributes),
        }
        self.assertEqual(resources['span'], resources['metric'])
        self.assertEqual(resources['span'], resources['log'])
        self.assertEqual(resources['span']['service.name'], 'hairmatch-api')
        self.assertEqual(resources['span']['service.version'], '9.9')
        self.assertEqual(resources['span']['deployment.environment.name'], 'dev')
        self.assertRegex(resources['span']['service.instance.id'], r'^[0-9a-f]{32}$')

    def test_log_record_carries_the_trace_context_and_a_redacted_exception(self):
        """TEL-39, TEL-40, TEL-46."""
        exporter = InMemoryLogRecordExporter()
        pipeline = self.build(log_exporter=exporter)
        logger = self.logger_for(pipeline)
        with pipeline.tracer_provider.get_tracer('t').start_as_current_span('request') as span:
            try:
                raise ValueError('dup key ana@example.com')
            except ValueError:
                logger.error('login of %s with cpf 123.456.789-09 failed', 'ana@example.com', exc_info=True)
        self.assertTrue(wait_for(lambda: exporter.get_finished_logs()))
        (item,) = exporter.get_finished_logs()
        record = item.log_record
        self.assertEqual(record.body, 'login of [email] with cpf [cpf] failed')
        self.assertEqual(record.severity_text, 'ERROR')
        self.assertEqual(record.trace_id, span.get_span_context().trace_id)
        self.assertEqual(record.span_id, span.get_span_context().span_id)
        self.assertEqual(record.attributes['exception.type'], 'ValueError')
        self.assertIn('ValueError: dup key [email]', record.attributes['exception.stacktrace'])
        self.assertNotIn('exception.message', record.attributes)
        self.assertNotIn('ana@example.com', repr(record.attributes) + str(record.body))

    def test_shutdown_returns_within_the_limit_even_when_an_exporter_blocks(self):
        """TEL-11: the three providers stop at the same time and the wait has a ceiling."""
        exporter = BlockingSpanExporter()
        pipeline = self.build(span_exporter=exporter)
        pipeline.tracer_provider.get_tracer('t').start_span('s').end()
        time.sleep(0.2)
        started = time.monotonic()
        pipeline.shutdown(timeout=1)
        self.assertLess(time.monotonic() - started, 1.5)
        exporter.release.set()
