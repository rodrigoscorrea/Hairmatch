"""
Telemetry for the test suite (#194): the same chain as production, with in-memory exporters.

The OpenTelemetry providers are process-wide and can be set once, so the test runner installs them once, before the
database connection opens (`install`), and each test empties what the previous one left (`clear`). Spans reach the exporter
through `SanitizingSpanProcessor`, the very processor production uses, so a test that looks for personal data in a span
looks at what production would send. The whole suite runs instrumented, which also proves TEL-13: a view does not notice it.
"""
import logging
import os
from types import SimpleNamespace

from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import InMemoryLogRecordExporter, SimpleLogRecordProcessor
from opentelemetry.sdk.metrics import (
    Counter, Histogram, MeterProvider, ObservableCounter, ObservableGauge, ObservableUpDownCounter, UpDownCounter,
)
from opentelemetry.sdk.metrics.export import AggregationTemporality, InMemoryMetricReader
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.sdk.trace.sampling import ALWAYS_ON, ParentBased

from . import otel
from .logs import RedactionFilter

_DELTA = {
    kind: AggregationTemporality.DELTA
    for kind in (Counter, UpDownCounter, Histogram, ObservableCounter, ObservableUpDownCounter, ObservableGauge)
}

_state = SimpleNamespace(installed=False, collected={})
span_exporter = InMemorySpanExporter()
log_exporter = InMemoryLogRecordExporter()
metric_reader = InMemoryMetricReader(preferred_temporality=_DELTA)


def install():
    """Installs the providers, the log handler and the instrumentation, once per process."""
    if _state.installed:
        return
    _state.installed = True
    os.environ.setdefault('OTEL_SEMCONV_STABILITY_OPT_IN', 'http')
    resource = otel.build_resource({})
    tracer_provider = TracerProvider(resource=resource, sampler=ParentBased(ALWAYS_ON), shutdown_on_exit=False)
    tracer_provider.add_span_processor(otel.SanitizingSpanProcessor(SimpleSpanProcessor(span_exporter)))
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader], shutdown_on_exit=False)
    logger_provider = LoggerProvider(resource=resource, shutdown_on_exit=False)
    logger_provider.add_log_record_processor(SimpleLogRecordProcessor(log_exporter))
    trace.set_tracer_provider(tracer_provider)
    metrics.set_meter_provider(meter_provider)
    set_logger_provider(logger_provider)
    handler = otel.OtlpLogHandler(logger_provider)
    handler.addFilter(RedactionFilter())
    logging.getLogger().addHandler(handler)
    otel._instrument(SimpleNamespace(tracer_provider=tracer_provider, meter_provider=meter_provider), '')


def spans():
    return list(span_exporter.get_finished_spans())


def log_records():
    return [item.log_record for item in log_exporter.get_finished_logs()]


def _collect():
    data = metric_reader.get_metrics_data()
    for resource in (data.resource_metrics if data else []):
        for scope in resource.scope_metrics:
            for metric in scope.metrics:
                _state.collected.setdefault(metric.name, []).append(metric)


def metric(name):
    """Every metric object named `name` collected since the last `clear`."""
    _collect()
    return _state.collected.get(name, [])


def points(name):
    """(attributes, value) of every counter data point of `name` since the last `clear`, merged by attributes."""
    merged = {}
    for item in metric(name):
        for point in item.data.data_points:
            key = tuple(sorted(point.attributes.items()))
            merged[key] = merged.get(key, 0) + point.value
    return [(dict(key), value) for key, value in merged.items()]


def clear():
    _collect()
    _state.collected.clear()
    span_exporter.clear()
    log_exporter.clear()


class TelemetryMixin:
    """For a TestCase: starts every test with nothing recorded and gives short names to the readers."""

    def setUp(self):
        super().setUp()
        clear()

    def spans(self):
        return spans()

    def span(self, name_prefix=None, kind=None):
        found = [
            s for s in spans()
            if (name_prefix is None or s.name.startswith(name_prefix)) and (kind is None or s.kind == kind)
        ]
        self.assertEqual(len(found), 1, [s.name for s in spans()])
        return found[0]

    def log_records(self):
        return log_records()

    def points(self, name):
        return points(name)
