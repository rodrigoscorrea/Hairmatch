"""
`GET /api/health` (#194, TEL-61 to TEL-65): whether the process is up and the database answers.

It checks nothing else on purpose: the Collector, AWS and the external providers must not take the
API out of rotation (TEL-64). The route is outside the HTTP instrumentation (`excluded_urls`), and the query
runs without tracing, so a probe leaves no span and no metric point (TEL-34).
"""
from django.db import connection
from django.http import JsonResponse
from rest_framework.views import APIView

from . import telemetry
from .problems import problem_response

DATABASE_DOWN_DETAIL = 'The database is not responding.'


class HealthView(APIView):
    # No session and no throttle: a monitor calls this every few seconds, with no cookie.
    authentication_classes = []
    permission_classes = []
    throttle_classes = []

    def get(self, request):
        try:
            with telemetry.untraced(), connection.cursor() as cursor:
                cursor.execute('SELECT 1')
                cursor.fetchone()
        except Exception:
            return problem_response(request, 'service-unavailable', DATABASE_DOWN_DETAIL)
        return JsonResponse({'status': 'ok'}, status=200)
