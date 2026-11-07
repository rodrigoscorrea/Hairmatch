"""
OpenTelemetry setup for the backend (#194, AD-016). This is the only module that knows the SDK, and only
`hairmatch/wsgi.py` starts it: management commands and the test runner never import the WSGI module (TEL-05).

The chain every span goes through is the same in production and in the tests: instrumentation -> SanitizingSpanProcessor
-> exporter. The sanitizer is what keeps personal data and device identifiers out of a span (TEL-47, TEL-48, TEL-86).
"""
import atexit
import logging
import os
import re
import signal
import threading
import time
import uuid
from urllib.parse import unquote, urlparse

from opentelemetry import metrics, trace
from opentelemetry._logs import LogRecord, SeverityNumber, set_logger_provider
from opentelemetry.context import get_current
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import Event, ReadableSpan, SpanProcessor, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ALWAYS_ON, ParentBased
from opentelemetry.trace import SpanKind, Status, StatusCode

from .logs import RedactionFilter
from .redaction import redact, sanitize_text

logger = logging.getLogger(__name__)

DEFAULT_SERVICE_NAME = 'hairmatch-api'
DEFAULT_ENVIRONMENT = 'dev'

# TEL-47, plus what identifies a client or a device. Header attributes and messaging.* are matched by prefix.
FORBIDDEN_ATTRIBUTES = frozenset({
    'url.query', 'url.full', 'url.path', 'http.url', 'http.target', 'client.address', 'enduser.id',
    'http.client_ip', 'net.peer.ip', 'network.peer.address', 'http.user_agent', 'user_agent.original',
})
FORBIDDEN_PREFIXES = ('http.request.header.', 'http.response.header.', 'messaging.')


def build_resource(environ=None):
    """
    The resource of every signal (TEL-29 to TEL-31). `OTEL_SERVICE_NAME` wins over `service.name` in
    `OTEL_RESOURCE_ATTRIBUTES`; an empty or missing version or environment is `dev`; the instance id is new on each call.
    """
    environ = os.environ if environ is None else environ
    given = {}
    for item in (environ.get('OTEL_RESOURCE_ATTRIBUTES') or '').split(','):
        key, separator, value = item.partition('=')
        if separator and key.strip() and value.strip():
            given[key.strip()] = unquote(value.strip())
    attributes = {
        **given,
        'service.name': (environ.get('OTEL_SERVICE_NAME') or '').strip() or given.get('service.name') or DEFAULT_SERVICE_NAME,
        'service.version': given.get('service.version') or DEFAULT_ENVIRONMENT,
        'deployment.environment.name': given.get('deployment.environment.name') or DEFAULT_ENVIRONMENT,
        'service.instance.id': uuid.uuid4().hex,
    }
    return Resource.create(attributes)


def _sanitize_value(value):
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, (list, tuple)):
        return type(value)(_sanitize_value(item) for item in value)
    return value


def _sanitize_attributes(attributes):
    return {
        key: _sanitize_value(value)
        for key, value in (attributes or {}).items()
        if key not in FORBIDDEN_ATTRIBUTES and not key.startswith(FORBIDDEN_PREFIXES)
    }


def sanitize_span(span):
    """A copy of the finished `span` without the forbidden attributes and with every text redacted (TEL-47, TEL-48, TEL-86)."""
    attributes = span.attributes or {}
    name, kind = span.name, span.kind
    if attributes.get('rpc.system') == 'aws-api' and attributes.get('rpc.service') and attributes.get('rpc.method'):
        # The SDK instrumentation names an SNS publish after the endpoint ARN, which identifies a device.
        name, kind = f"{attributes['rpc.service']}.{attributes['rpc.method']}", SpanKind.CLIENT
    status = span.status
    if status is not None and status.description:
        status = Status(status.status_code, sanitize_text(status.description))
    return ReadableSpan(
        name=sanitize_text(name),
        context=span.context,
        parent=span.parent,
        resource=span.resource,
        attributes=_sanitize_attributes(attributes),
        events=[Event(event.name, _sanitize_attributes(event.attributes), event.timestamp) for event in span.events],
        links=span.links,
        kind=kind,
        status=status,
        start_time=span.start_time,
        end_time=span.end_time,
        instrumentation_scope=span.instrumentation_scope,
    )


class SanitizingSpanProcessor(SpanProcessor):
    """Hands the next processor a sanitized copy of each finished span. A span that cannot be sanitized is dropped, never exported raw."""

    def __init__(self, inner):
        self._inner = inner

    def on_start(self, span, parent_context=None):
        self._inner.on_start(span, parent_context)

    def on_end(self, span):
        try:
            clean = sanitize_span(span)
        except Exception:
            logger.warning('a span was dropped because it could not be sanitized')
            return
        self._inner.on_end(clean)

    def shutdown(self):
        self._inner.shutdown()

    def force_flush(self, timeout_millis=30000):
        return self._inner.force_flush(timeout_millis)


# Limits of the export (TEL-07, TEL-08): a stopped Collector must neither hold a request, nor hold a restart, nor grow the memory.
EXPORT_TIMEOUT_SECONDS = 2
QUEUE_SIZE = 2048
METRIC_INTERVAL_MILLIS = 15000
SHUTDOWN_SECONDS = 4

# The request path the Django instrumentation leaves out (TEL-34). It matches the absolute URL, with or without a query string.
HEALTH_EXCLUDED_URLS = r'/api/health/?(\?.*)?$'

_SEVERITY = {
    logging.DEBUG: SeverityNumber.DEBUG,
    logging.INFO: SeverityNumber.INFO,
    logging.WARNING: SeverityNumber.WARN,
    logging.ERROR: SeverityNumber.ERROR,
    logging.CRITICAL: SeverityNumber.FATAL,
}
_STANDARD_RECORD_FIELDS = frozenset(vars(logging.LogRecord('', 0, '', 0, '', (), None))) | {'message', 'asctime', 'taskName'}


class OtlpLogHandler(logging.Handler):
    """
    Sends each record to the Collector with the trace context of the calling thread (TEL-39). The exception goes as
    its type and its stack text only; the filter in front of this handler already redacted the message and the stack.
    """

    def __init__(self, logger_provider):
        super().__init__()
        self._provider = logger_provider

    def emit(self, record):
        try:
            attributes = {
                key: redact(value) if isinstance(value, str) else value
                for key, value in vars(record).items()
                if key not in _STANDARD_RECORD_FIELDS and isinstance(value, (str, int, float, bool))
            }
            if record.exc_info and record.exc_info[0] is not None:
                attributes['exception.type'] = record.exc_info[0].__name__
                attributes['exception.stacktrace'] = redact(record.exc_text or logging.Formatter().formatException(record.exc_info))
            self._provider.get_logger(record.name).emit(LogRecord(
                timestamp=int(record.created * 1e9),
                observed_timestamp=time.time_ns(),
                context=get_current(),
                severity_text={'WARNING': 'WARN', 'CRITICAL': 'FATAL'}.get(record.levelname, record.levelname),
                severity_number=_SEVERITY.get(record.levelno, SeverityNumber.INFO),
                body=record.getMessage(),
                attributes=attributes,
            ))
        except Exception:
            self.handleError(record)


class Pipeline:
    """The three providers, built around the exporters they are given."""

    def __init__(self, resource, span_exporter, metric_exporter, log_exporter, metric_interval_millis=METRIC_INTERVAL_MILLIS):
        self.resource = resource
        # The sampler is explicit: OTEL_TRACES_SAMPLER must not change the "100% unless the parent says no" rule (TEL-35, TEL-82).
        self.tracer_provider = TracerProvider(resource=resource, sampler=ParentBased(ALWAYS_ON), shutdown_on_exit=False)
        self.tracer_provider.add_span_processor(SanitizingSpanProcessor(BatchSpanProcessor(
            span_exporter, max_queue_size=QUEUE_SIZE, export_timeout_millis=EXPORT_TIMEOUT_SECONDS * 1000,
        )))
        self.meter_provider = MeterProvider(
            resource=resource,
            metric_readers=[PeriodicExportingMetricReader(
                metric_exporter,
                export_interval_millis=metric_interval_millis,
                export_timeout_millis=EXPORT_TIMEOUT_SECONDS * 1000,
            )],
            shutdown_on_exit=False,
        )
        self.logger_provider = LoggerProvider(resource=resource, shutdown_on_exit=False)
        self.logger_provider.add_log_record_processor(BatchLogRecordProcessor(
            log_exporter, max_queue_size=QUEUE_SIZE, export_timeout_millis=EXPORT_TIMEOUT_SECONDS * 1000,
        ))
        self._closed = False

    def log_handler(self):
        handler = OtlpLogHandler(self.logger_provider)
        handler.addFilter(RedactionFilter())
        return handler

    def shutdown(self, timeout=SHUTDOWN_SECONDS):
        """Shuts the three providers down at the same time, so a dead Collector costs one wait and not three (TEL-11)."""
        if self._closed:
            return
        self._closed = True
        threads = [
            threading.Thread(target=provider.shutdown, daemon=True)
            for provider in (self.tracer_provider, self.meter_provider, self.logger_provider)
        ]
        deadline = time.monotonic() + timeout
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(max(0.0, deadline - time.monotonic()))


_state = {'pipeline': None}
_start_lock = threading.Lock()


def _instrument(pipeline, endpoint):
    from opentelemetry.instrumentation.botocore import BotocoreInstrumentor
    from opentelemetry.instrumentation.botocore.extensions import _BOTOCORE_EXTENSIONS
    from opentelemetry.instrumentation.django import DjangoInstrumentor
    from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor

    # The extension of SNS names the span after the endpoint ARN and adds MessageAttributes to the publish.
    _BOTOCORE_EXTENSIONS.pop('sns', None)
    providers = {'tracer_provider': pipeline.tracer_provider, 'meter_provider': pipeline.meter_provider}
    DjangoInstrumentor().instrument(excluded_urls=HEALTH_EXCLUDED_URLS, **providers)
    Psycopg2Instrumentor().instrument(**providers)
    BotocoreInstrumentor().instrument(**providers)
    # The exporter reaches the Collector through the same HTTP client: its own calls are not traced.
    exporter_host = re.escape(urlparse(endpoint).netloc)
    RequestsInstrumentor().instrument(excluded_urls=exporter_host or None, **providers)


def _on_sigterm(signum, frame):
    shutdown()
    signal.signal(signal.SIGTERM, signal.SIG_DFL)
    os.kill(os.getpid(), signal.SIGTERM)


def start(environ=None):
    """Installs the providers, the OTLP log handler and the instrumentation. Called once per process by `telemetry.init_telemetry`."""
    environ = os.environ if environ is None else environ
    endpoint = (environ.get('OTEL_EXPORTER_OTLP_ENDPOINT') or '').strip()
    from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

    with _start_lock:
        if _state['pipeline'] is not None:
            return True
        # The stable HTTP conventions give http.server.request.duration in seconds with http.route (TEL-32).
        os.environ.setdefault('OTEL_SEMCONV_STABILITY_OPT_IN', 'http')
        pipeline = Pipeline(
            build_resource(environ),
            OTLPSpanExporter(timeout=EXPORT_TIMEOUT_SECONDS),
            OTLPMetricExporter(timeout=EXPORT_TIMEOUT_SECONDS),
            OTLPLogExporter(timeout=EXPORT_TIMEOUT_SECONDS),
        )
        trace.set_tracer_provider(pipeline.tracer_provider)
        metrics.set_meter_provider(pipeline.meter_provider)
        set_logger_provider(pipeline.logger_provider)
        _state['pipeline'] = pipeline
        # Django's LOGGING (the `otlp` handler) puts the handler on the root logger when `django.setup()` runs after
        # this; added here too for a start that comes later. dictConfig replaces the root handlers, so there is never a second one.
        logging.getLogger().addHandler(pipeline.log_handler())
        _instrument(pipeline, endpoint)
        atexit.register(shutdown)
        # runserver --noreload and Gunicorn-less runs end on the default SIGTERM, which skips atexit.
        if threading.current_thread() is threading.main_thread() and signal.getsignal(signal.SIGTERM) is signal.SIG_DFL:
            signal.signal(signal.SIGTERM, _on_sigterm)
        return True


def shutdown(timeout=SHUTDOWN_SECONDS):
    """Flushes and stops the providers within `timeout` seconds. Safe to call more than once."""
    with _start_lock:
        pipeline, _state['pipeline'] = _state['pipeline'], None
    root = logging.getLogger()
    for handler in [h for h in root.handlers if isinstance(h, OtlpLogHandler)]:
        root.removeHandler(handler)
    if pipeline is not None:
        pipeline.shutdown(timeout)
