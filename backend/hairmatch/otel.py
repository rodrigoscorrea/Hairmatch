"""
OpenTelemetry setup for the backend (#194, AD-016). This is the only module that knows the SDK, and only
`hairmatch/wsgi.py` starts it: management commands and the test runner never import the WSGI module (TEL-05).

The chain every span goes through is the same in production and in the tests: instrumentation -> SanitizingSpanProcessor
-> exporter. The sanitizer is what keeps personal data and device identifiers out of a span (TEL-47, TEL-48, TEL-86).
"""
import logging
import os
import uuid
from urllib.parse import unquote

from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import Event, ReadableSpan, SpanProcessor
from opentelemetry.trace import SpanKind, Status, StatusCode

from .redaction import sanitize_text

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
