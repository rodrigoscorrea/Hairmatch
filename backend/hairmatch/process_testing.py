"""Helpers for the tests that need a fresh interpreter: the providers of OpenTelemetry are process-wide and cannot be undone."""
import json
import os
import subprocess
import sys

from django.conf import settings

REPORT_PREFIX = 'REPORT '


def run_python(code, env=None, timeout=120):
    """
    Runs `code` in a fresh interpreter from the backend directory, with the real settings and
    without `OTEL_EXPORTER_OTLP_ENDPOINT` unless `env` sets it. Returns (report, log lines, stderr),
    where `report` is the JSON the code printed with `print('REPORT ' + json.dumps(...))`.
    """
    full_env = {**os.environ, 'DJANGO_SETTINGS_MODULE': 'hairmatch.settings'}
    for name in ('OTEL_EXPORTER_OTLP_ENDPOINT', 'OTEL_SERVICE_NAME', 'OTEL_RESOURCE_ATTRIBUTES'):
        full_env.pop(name, None)
    full_env.update(env or {})
    done = subprocess.run(
        [sys.executable, '-W', 'ignore', '-c', code],
        cwd=settings.BASE_DIR, env=full_env, capture_output=True, text=True, timeout=timeout,
    )
    if done.returncode != 0:
        raise AssertionError(f'subprocess failed ({done.returncode}):\n{done.stdout}\n{done.stderr}')
    report, logs = None, []
    for line in done.stdout.splitlines():
        if line.startswith(REPORT_PREFIX):
            report = json.loads(line[len(REPORT_PREFIX):])
        elif line.startswith('{'):
            logs.append(json.loads(line))
    return report, logs, done.stderr
