"""
The parts of the LOGGING configuration (#194): a JSON line per record, the trace ids, the redaction
and the throttle of export errors. Nothing here imports the OpenTelemetry SDK, so logging works the
same with the telemetry off.
"""
import copy
import logging
import threading
import time

from pythonjsonlogger.json import JsonFormatter as BaseJsonFormatter

from .redaction import redact

_EXPORT_ERROR_WINDOW_SECONDS = 60


class JsonFormatter(BaseJsonFormatter):
    """One JSON object per record with `ts`, `level`, `name` and `message`; the traceback goes in `exc_info`."""

    def __init__(self, **kwargs):
        kwargs.setdefault('rename_fields', {'levelname': 'level'})
        kwargs.setdefault('timestamp', 'ts')
        super().__init__('%(levelname)s %(name)s %(message)s', **kwargs)

    def formatException(self, ei):
        return redact(super().formatException(ei))

    def formatStack(self, stack_info):
        return redact(super().formatStack(stack_info))


class TraceContextFilter(logging.Filter):
    """Adds `trace_id` (32 hex) and `span_id` (16 hex) of the active span. Without a valid span the fields are absent."""

    def filter(self, record):
        try:
            from opentelemetry import trace

            context = trace.get_current_span().get_span_context()
            if context.is_valid:
                record.trace_id = format(context.trace_id, '032x')
                record.span_id = format(context.span_id, '016x')
        except Exception:
            pass
        return True


class RedactionFilter(logging.Filter):
    """
    Redacts the message, the traceback and the stack text (TEL-44, TEL-45). It returns a copy, so the handler
    that runs next (stdout or OTLP) never sees another handler's changes. Python 3.12 lets a filter return a record.
    """

    def filter(self, record):
        clean = copy.copy(record)
        clean.msg = redact(record.getMessage())
        clean.args = ()
        if record.exc_info and not record.exc_text:
            clean.exc_text = logging.Formatter().formatException(record.exc_info)
        if clean.exc_text:
            clean.exc_text = redact(clean.exc_text)
        if record.stack_info:
            clean.stack_info = redact(record.stack_info)
        return clean


class ExportErrorRateLimit(logging.Filter):
    """At most one warning or error per signal every 60 seconds from the `opentelemetry` loggers (TEL-15)."""

    def __init__(self, name='', window=_EXPORT_ERROR_WINDOW_SECONDS, clock=time.monotonic):
        super().__init__(name)
        self._window = window
        self._clock = clock
        self._last = {}
        self._lock = threading.Lock()

    @staticmethod
    def _signal(logger_name):
        lowered = logger_name.lower()
        for signal, hints in (('traces', ('trace', 'span')), ('metrics', ('metric',)), ('logs', ('log',))):
            if any(hint in lowered for hint in hints):
                return signal
        return logger_name

    def filter(self, record):
        if record.levelno < logging.WARNING:
            return True
        key = self._signal(record.name)
        now = self._clock()
        with self._lock:
            last = self._last.get(key)
            if last is not None and now - last < self._window:
                return False
            self._last[key] = now
        return True


class StripQueryString(logging.Filter):
    """The access log of `runserver` (`django.server`) without the query string and without the socket in `extra` (TEL-43)."""

    def filter(self, record):
        clean = copy.copy(record)
        clean.__dict__.pop('request', None)
        args = record.args
        if isinstance(args, tuple) and args and isinstance(args[0], str):
            parts = args[0].split(' ')
            if len(parts) == 3:
                parts[1] = parts[1].split('?', 1)[0]
                clean.args = (' '.join(parts),) + args[1:]
        return clean
