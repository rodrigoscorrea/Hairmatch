"""
WSGI config for hairmatch project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hairmatch.settings')

# The only place the telemetry starts from the environment (TEL-05): the Django instrumentation adds its middleware to
# settings.MIDDLEWARE, so it must run before the application loads the middleware. Management commands and the test
# runner never import this module. A Gunicorn config can call init_telemetry() from post_fork instead.
from hairmatch.telemetry import init_telemetry, log_init_failure

init_telemetry()

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()

# The logging is configured now, so the warning of a failed start goes out as a JSON line like every other log.
log_init_failure()
