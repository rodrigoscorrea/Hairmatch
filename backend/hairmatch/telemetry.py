"""
What the business code calls to emit telemetry (#194, AD-016).

Only the OpenTelemetry API is used here, and it does nothing until `hairmatch.otel` installs the SDK, so
these helpers are no-ops with the telemetry off (TEL-12). No helper raises: an error from the SDK is swallowed,
and the view answers as it would without telemetry (TEL-13). The business counters have closed label sets: a value
outside the set is not recorded, which keeps the cardinality bounded (TEL-60) and the labels free of personal data.
"""
import logging
import threading
from contextlib import contextmanager

logger = logging.getLogger(__name__)

METER_NAME = 'hairmatch'

# name -> (description, {label: allowed values or None for "checked by a function"})
COUNTERS = {
    'hairmatch.problems': ('Error responses by slug and status.', {'slug': None, 'status': None}),
    'hairmatch.reserves.created': ('Reservations created.', {'channel': {'app', 'whatsapp'}}),
    'hairmatch.push.results': (
        'Push attempts by result.', {'outcome': {'published', 'endpoint_gone', 'unavailable', 'error'}},
    ),
    'hairmatch.auth.rejections': (
        'Sessions the authenticator refused.', {'reason': {'missing', 'expired', 'invalid', 'unavailable'}},
    ),
    'hairmatch.signup.events': (
        'Steps of the e-mail signup.', {'step': {'created', 'confirmed', 'resent', 'throttled'}},
    ),
    'hairmatch.uploads': (
        'Image uploads.',
        {'kind': {'profile', 'review', 'gallery'}, 'outcome': {'stored', 'invalid_image', 'failed'}},
    ),
    'hairmatch.cep.lookups': (
        'Postal code lookups by source.', {'source': {'cache', 'viacep', 'brasilapi', 'not_found', 'unavailable'}},
    ),
    'hairmatch.ai.requests': (
        'Gemini calls.', {'feature': {'profile', 'chatbot'}, 'outcome': {'ok', 'error'}},
    ),
    'hairmatch.ai.tokens': (
        'Gemini tokens.', {'feature': {'profile', 'chatbot'}, 'direction': {'input', 'output'}},
    ),
}

_counters = {}
_lock = threading.RLock()
_warned = set()
_init = {'done': False, 'enabled': False, 'failure': None, 'logged': False}


def init_telemetry(environ=None):
    """
    Starts the SDK once per process, only when `OTEL_EXPORTER_OTLP_ENDPOINT` is set (TEL-01, TEL-04). Without it
    nothing is imported, opened or logged (TEL-02). A failure logs one WARNING with the exception type and the
    app goes on without telemetry (TEL-03). Never raises. Gunicorn's `post_fork` can call it later.
    """
    import os

    environ = os.environ if environ is None else environ
    with _lock:
        if _init['done']:
            return _init['enabled']
        _init['done'] = True
        if not (environ.get('OTEL_EXPORTER_OTLP_ENDPOINT') or '').strip():
            return False
        try:
            from hairmatch import otel

            _init['enabled'] = bool(otel.start(environ))
        except BaseException as exc:
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            # The type only: the message of an SDK error can carry the endpoint or a header.
            _init['failure'] = type(exc).__name__
            _init['enabled'] = False
        # From `hairmatch.wsgi` Django has not configured the logging yet; it calls log_init_failure() afterwards.
        if logging.getLogger().handlers:
            log_init_failure()
        return _init['enabled']


def log_init_failure():
    """Logs the one WARNING of a failed start (TEL-03), the first time it is called after the failure."""
    with _lock:
        failure = _init['failure']
        if failure is None or _init['logged']:
            return
        _init['logged'] = True
    logger.warning('telemetry disabled, the SDK failed to start: %s', failure)


def _meter():
    from opentelemetry import metrics

    return metrics.get_meter(METER_NAME)


def _tracer():
    from opentelemetry import trace

    return trace.get_tracer(METER_NAME)


def _valid_problem_labels(labels):
    from hairmatch.problems import CATALOG

    status = labels.get('status')
    return labels.get('slug') in CATALOG and isinstance(status, int) and not isinstance(status, bool) and 400 <= status <= 599


def _labels_are_valid(name, labels):
    allowed = COUNTERS[name][1]
    if set(labels) != set(allowed):
        return False
    if name == 'hairmatch.problems':
        return _valid_problem_labels(labels)
    return all(labels[label] in values for label, values in allowed.items())


def _add(name, amount, **labels):
    try:
        if not _labels_are_valid(name, labels):
            if name not in _warned:
                _warned.add(name)
                logger.warning('telemetry: %s dropped, a label is outside its closed set', name)
            return
        with _lock:
            counter = _counters.get(name)
            if counter is None:
                counter = _counters[name] = _meter().create_counter(name, unit='1', description=COUNTERS[name][0])
        counter.add(amount, labels)
    except Exception:
        pass


def count_problem(slug, status):
    _add('hairmatch.problems', 1, slug=slug, status=status)


def count_reserve_created(channel):
    _add('hairmatch.reserves.created', 1, channel=channel)


def count_push(outcome):
    _add('hairmatch.push.results', 1, outcome=outcome)


def count_auth_rejection(reason):
    _add('hairmatch.auth.rejections', 1, reason=reason)


def count_signup(step):
    _add('hairmatch.signup.events', 1, step=step)


def count_upload(kind, outcome):
    _add('hairmatch.uploads', 1, kind=kind, outcome=outcome)


def count_cep_lookup(source):
    _add('hairmatch.cep.lookups', 1, source=source)


def count_ai_request(feature, outcome):
    _add('hairmatch.ai.requests', 1, feature=feature, outcome=outcome)


def count_ai_tokens(feature, direction, amount):
    if isinstance(amount, int) and not isinstance(amount, bool) and amount > 0:
        _add('hairmatch.ai.tokens', amount, feature=feature, direction=direction)


def _clean_attributes(attributes):
    return {key: value for key, value in attributes.items() if value is not None}


def set_span_attributes(**attributes):
    """Sets attributes on the active span (the request's, in a view). Pass the full key: `**{'hairmatch.reserve_id': 7}`."""
    try:
        from opentelemetry import trace

        trace.get_current_span().set_attributes(_clean_attributes(attributes))
    except Exception:
        pass


@contextmanager
def span(name, **attributes):
    """
    A child span of the active one. The body's exceptions pass through untouched, after the span is marked
    as an error with the exception type only (the message may carry personal data).
    """
    manager = None
    current = None
    try:
        manager = _tracer().start_as_current_span(
            name, attributes=_clean_attributes(attributes), record_exception=False, set_status_on_exception=False,
        )
        current = manager.__enter__()
    except Exception:
        manager = None
    try:
        yield current
    except BaseException as exc:
        _mark_error(current, exc)
        raise
    finally:
        if manager is not None:
            try:
                manager.__exit__(None, None, None)
            except Exception:
                pass


def _mark_error(current, exc):
    if current is None:
        return
    try:
        from opentelemetry.trace import Status, StatusCode

        current.set_attribute('error.type', type(exc).__name__)
        current.set_status(Status(StatusCode.ERROR, type(exc).__name__))
    except Exception:
        pass


class GeminiCall:
    """Handed to the code that calls Gemini, to record the token usage of the response."""

    def __init__(self, feature, current):
        self._feature = feature
        self._span = current

    def record_usage(self, response):
        try:
            usage = getattr(response, 'usage_metadata', None)
            for direction, field in (('input', 'prompt_token_count'), ('output', 'candidates_token_count')):
                tokens = getattr(usage, field, None)
                if isinstance(tokens, int) and not isinstance(tokens, bool):
                    if self._span is not None:
                        self._span.set_attribute(f'gen_ai.usage.{direction}_tokens', tokens)
                    count_ai_tokens(self._feature, direction, tokens)
        except Exception:
            pass


@contextmanager
def gemini_call(feature, model):
    """
    Span `gemini generate_content` and the `ai.requests` counter around one call to Gemini. The prompt and
    the answer are never recorded. An exception from the body is re-raised after the span and the counter record the error.
    """
    with span('gemini generate_content', **{'gen_ai.request.model': model, 'hairmatch.ai.feature': feature}) as current:
        try:
            yield GeminiCall(feature, current)
        except BaseException:
            count_ai_request(feature, 'error')
            raise
        count_ai_request(feature, 'ok')
