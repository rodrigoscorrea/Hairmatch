"""
Continuous profiling for the backend (Pyroscope), next to the telemetry of `hairmatch.telemetry`.

It does nothing unless `PYROSCOPE_SERVER_ADDRESS` is set: nothing is imported, no thread starts and no connection
opens. It never raises: a failure is remembered and logged once as a WARNING with the exception type only (the message
of an SDK error can carry the address), and the app goes on without profiling. The agent runs inside the process and
pushes the profiles straight to the Pyroscope server, not through the OpenTelemetry Collector.

`hairmatch.wsgi` starts it, so only the process that serves requests is profiled: the autoreloader parent of
`runserver` never imports the WSGI module.
"""
import logging
import os
import threading

logger = logging.getLogger(__name__)

DEFAULT_SERVICE_NAME = 'hairmatch-api'
DEFAULT_ENVIRONMENT = 'dev'

_lock = threading.RLock()
_init = {'done': False, 'enabled': False, 'failure': None, 'logged': False}


def _resource_attributes(environ):
    given = {}
    for item in (environ.get('OTEL_RESOURCE_ATTRIBUTES') or '').split(','):
        key, sep, value = item.partition('=')
        if sep and key.strip():
            given[key.strip()] = value.strip()
    return given


def service_name(environ=None):
    """The same name the telemetry uses: OTEL_SERVICE_NAME, then service.name in OTEL_RESOURCE_ATTRIBUTES, then the default."""
    environ = os.environ if environ is None else environ
    return (
        (environ.get('OTEL_SERVICE_NAME') or '').strip()
        or _resource_attributes(environ).get('service.name')
        or DEFAULT_SERVICE_NAME
    )


def init_profiling(environ=None):
    """Starts the Pyroscope agent once per process when `PYROSCOPE_SERVER_ADDRESS` is set. Returns whether it is running."""
    environ = os.environ if environ is None else environ
    with _lock:
        if _init['done']:
            return _init['enabled']
        _init['done'] = True
        address = (environ.get('PYROSCOPE_SERVER_ADDRESS') or '').strip()
        if not address:
            return False
        try:
            import pyroscope

            pyroscope.configure(
                application_name=service_name(environ),
                server_address=address,
                tags={'env': _resource_attributes(environ).get('deployment.environment.name') or DEFAULT_ENVIRONMENT},
            )
            _init['enabled'] = True
        except BaseException as exc:
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            _init['failure'] = type(exc).__name__
            _init['enabled'] = False
        # From `hairmatch.wsgi` Django has not configured the logging yet; it calls log_init_failure() afterwards.
        if logging.getLogger().handlers:
            log_init_failure()
        return _init['enabled']


def log_init_failure():
    """Logs the one WARNING of a failed start, the first time it is called after the failure."""
    with _lock:
        failure = _init['failure']
        if failure is None or _init['logged']:
            return
        _init['logged'] = True
    logger.warning('profiling disabled, the Pyroscope agent failed to start: %s', failure)
