"""
Error responses in the RFC 9457 format (Problem Details for HTTP APIs).

Every error under /api/ leaves through `problem_response`: views return it, helpers
raise `Problem`, and `exception_handler` maps framework errors and unexpected
exceptions to it. The catalog below is the contract with the app, which translates
each error by the slug at the end of `type`.
"""
import json
import logging
import math

from django.conf import settings
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import exceptions

logger = logging.getLogger(__name__)

PROBLEM_CONTENT_TYPE = 'application/problem+json'

# slug -> (status, title)
CATALOG = {
    'validation-error': (400, 'Invalid request data'),
    'malformed-request': (400, 'Malformed request'),
    'invalid-image': (400, 'Invalid image'),
    'invalid-postal-code': (400, 'Invalid postal code'),
    'password-policy': (400, 'Password does not meet the policy'),
    'incorrect-current-password': (400, 'Incorrect current password'),
    'email-change-unsupported': (400, 'Email change not supported'),
    'invalid-session': (401, 'Invalid or expired session'),
    'invalid-credentials': (401, 'Invalid credentials'),
    'session-expired': (401, 'Session expired'),
    'invalid-google-token': (401, 'Invalid Google token'),
    'signup-session-expired': (401, 'Signup session expired'),
    'forbidden': (403, 'Forbidden'),
    'hairdresser-required': (403, 'Hairdresser account required'),
    'customer-required': (403, 'Customer account required'),
    'google-account-login': (403, 'Account uses Google sign-in'),
    'google-email-unverified': (403, 'Google email not verified'),
    'not-found': (404, 'Resource not found'),
    'postal-code-not-found': (404, 'Postal code not found'),
    'method-not-allowed': (405, 'Method not allowed'),
    'email-taken': (409, 'Email already registered'),
    'phone-taken': (409, 'Phone already registered'),
    'google-account-taken': (409, 'Google account already registered'),
    'google-email-linked': (409, 'Email linked to another Google account'),
    'availability-exists': (409, 'Availability already exists'),
    'agenda-overlap': (409, 'Agenda slot overlaps'),
    'service-has-reservations': (409, 'Service has reservations'),
    'review-exists': (409, 'Reservation already reviewed'),
    'slot-unavailable': (409, 'Time slot unavailable'),
    'customer-schedule-conflict': (409, 'Customer schedule conflict'),
    'unsupported-media-type': (415, 'Unsupported media type'),
    'too-many-requests': (429, 'Too many requests'),
    'internal-error': (500, 'Internal server error'),
    'auth-unavailable': (503, 'Authentication service unavailable'),
    'postal-code-service-unavailable': (503, 'Postal code service unavailable'),
    'ai-service-unavailable': (503, 'AI service unavailable'),
}


class Problem(Exception):
    """An error the client must see as a problem+json response; `exception_handler` renders it."""

    def __init__(self, slug, detail, errors=None):
        super().__init__(slug, detail)
        self.slug = slug
        self.detail = detail
        self.errors = errors


def problem_response(request, slug, detail, errors=None, headers=None, status=None):
    """
    The problem+json response for `slug`. `detail` is an English sentence about this occurrence,
    never exception text. `errors` is only for `validation-error`. `status` overrides the catalog's
    only for a framework error that has no slug of its own.
    """
    catalog_status, title = CATALOG[slug]
    body = {
        'type': f'{settings.PROBLEM_TYPE_BASE_URI}{slug}',
        'title': title,
        'status': status or catalog_status,
        'detail': detail,
        'instance': request.path,
    }
    if errors is not None:
        body['errors'] = errors
    response = JsonResponse(body, status=body['status'], content_type=PROBLEM_CONTENT_TYPE)
    for name, value in (headers or {}).items():
        response[name] = value
    return response


def body_error(field, detail):
    """An `errors` item for a request body field, as a JSON Pointer."""
    return {'pointer': f'#/{field}', 'detail': detail}


def query_error(name, detail):
    """An `errors` item for a query string parameter, which a JSON Pointer cannot address."""
    return {'parameter': name, 'detail': detail}


def missing_field_errors(data, fields):
    """One `errors` item per field of `fields` that is absent or empty in `data`."""
    return [body_error(field, 'This field is required.') for field in fields if not data.get(field)]


def validation_problem(errors):
    return Problem('validation-error', 'One or more fields are invalid.', list(errors))


def json_object(request):
    """The request body as a dict. Raises Problem('malformed-request') when it is not a JSON object."""
    try:
        data = json.loads(request.body)
    except ValueError as exc:  # JSONDecodeError and UnicodeDecodeError
        raise Problem('malformed-request', 'The request body is not valid JSON.') from exc
    if not isinstance(data, dict):
        raise Problem('malformed-request', 'The request body must be a JSON object.')
    return data


def request_data(request):
    """`request.data` of a view that lets DRF parse the body, guaranteed to be a mapping."""
    data = request.data
    if not hasattr(data, 'get'):
        raise Problem('malformed-request', 'The request body must be a JSON object.')
    return data


def _sentence(message):
    message = str(message).strip()
    return message if message.endswith(('.', '!', '?')) else f'{message}.'


def _drf_validation_errors(detail):
    """Flattens the detail of a DRF ValidationError into `errors` items."""
    if isinstance(detail, dict):
        return [
            body_error(field, _sentence(message))
            for field, messages in detail.items()
            for message in (messages if isinstance(messages, list) else [messages])
        ]
    messages = detail if isinstance(detail, list) else [detail]
    return [{'pointer': '#', 'detail': _sentence(message)} for message in messages]


def exception_handler(exc, context):
    """
    DRF's exception handler. Unlike the default, it answers for every exception: a `None`
    would make DRF re-raise, and with DEBUG=True Django would serve its HTML error page.
    """
    request = context['request']

    if isinstance(exc, Problem):
        return problem_response(request, exc.slug, exc.detail, exc.errors)
    if isinstance(exc, exceptions.ValidationError):
        return problem_response(
            request, 'validation-error', 'One or more fields are invalid.', _drf_validation_errors(exc.detail)
        )
    if isinstance(exc, exceptions.ParseError):
        return problem_response(request, 'malformed-request', 'The request body could not be parsed.')
    if isinstance(exc, exceptions.MethodNotAllowed):
        return problem_response(request, 'method-not-allowed', 'This route does not support the request method.')
    if isinstance(exc, exceptions.UnsupportedMediaType):
        return problem_response(request, 'unsupported-media-type', 'The request content type is not supported.')
    if isinstance(exc, (exceptions.NotAuthenticated, exceptions.AuthenticationFailed)):
        return problem_response(request, 'invalid-session', 'Your session is missing, invalid or expired.')
    if isinstance(exc, (exceptions.PermissionDenied, DjangoPermissionDenied)):
        return problem_response(request, 'forbidden', 'You do not have permission to access this resource.')
    if isinstance(exc, (exceptions.NotFound, Http404)):
        return problem_response(request, 'not-found', 'Resource not found.')
    if isinstance(exc, exceptions.Throttled):
        headers = {'Retry-After': str(math.ceil(exc.wait))} if exc.wait is not None else None
        return problem_response(request, 'too-many-requests', 'Too many requests. Try again later.', headers=headers)
    if isinstance(exc, exceptions.APIException) and exc.status_code < 500:
        return problem_response(
            request, 'malformed-request', 'The request could not be processed.', status=exc.status_code
        )

    logger.error('Unhandled exception on %s %s', request.method, request.path, exc_info=exc)
    return problem_response(request, 'internal-error', 'An unexpected error occurred.')


@csrf_exempt
def api_not_found(request):
    """Last route under /api/: a URL that matches nothing. Any method, so the CSRF check must not run."""
    return problem_response(request, 'not-found', 'Resource not found.')
