import json
from unittest.mock import patch

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from django.urls import path
from django.test import Client, RequestFactory, TestCase, override_settings
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.test import APIClient

from hairmatch.problem_testing import assert_problem
from hairmatch.problems import (
    CATALOG,
    Problem,
    ProblemDetailsMiddleware,
    body_error,
    exception_handler,
    json_object,
    missing_field_errors,
    problem_response,
    query_error,
    validation_problem,
)
from users.views import CepLookupThrottle


def handle(exc, path='/api/anything', method='GET'):
    request = RequestFactory().generic(method, path)
    return exception_handler(exc, {'request': request})


class CatalogTest(TestCase):
    """PD-01 to PD-05: the shape every problem shares."""

    def test_catalog_has_the_36_slugs_of_the_spec(self):
        self.assertEqual(len(CATALOG), 36)

    def test_every_slug_builds_a_well_formed_problem(self):
        request = RequestFactory().get('/api/x?secret=1')
        for slug, (status, title) in CATALOG.items():
            with self.subTest(slug=slug):
                errors = [body_error('name', 'Bad.')] if slug == 'validation-error' else None
                response = problem_response(request, slug, 'Something happened.', errors=errors)
                body = assert_problem(response, slug, detail='Something happened.')
                self.assertNotEqual(body['type'], 'about:blank')
                self.assertEqual(body['instance'], '/api/x')

    def test_status_override_is_used_for_framework_errors_without_a_slug(self):
        response = problem_response(RequestFactory().get('/api/x'), 'malformed-request', 'Nope.', status=406)
        self.assertEqual(response.status_code, 406)
        self.assertEqual(json.loads(response.content)['status'], 406)

    def test_query_error_uses_parameter_and_body_error_uses_pointer(self):
        self.assertEqual(body_error('phone', 'Too short.'), {'pointer': '#/phone', 'detail': 'Too short.'})
        self.assertEqual(query_error('date', 'Bad.'), {'parameter': 'date', 'detail': 'Bad.'})

    def test_same_field_can_appear_twice_in_errors(self):
        """PD-111"""
        problem = validation_problem([body_error('phone', 'Too short.'), body_error('phone', 'Taken.')])
        self.assertEqual([item['pointer'] for item in problem.errors], ['#/phone', '#/phone'])

    def test_missing_field_errors_lists_each_absent_or_empty_field(self):
        errors = missing_field_errors({'a': 'x', 'b': ''}, ['a', 'b', 'c'])
        self.assertEqual([item['pointer'] for item in errors], ['#/b', '#/c'])


class JsonObjectTest(TestCase):
    def test_returns_the_dict(self):
        request = RequestFactory().post('/api/x', data='{"a": 1}', content_type='application/json')
        self.assertEqual(json_object(request), {'a': 1})

    def test_invalid_json_is_malformed_request(self):
        request = RequestFactory().post('/api/x', data='{nope', content_type='application/json')
        with self.assertRaises(Problem) as ctx:
            json_object(request)
        self.assertEqual(ctx.exception.slug, 'malformed-request')

    def test_json_that_is_not_an_object_is_malformed_request(self):
        request = RequestFactory().post('/api/x', data='[1]', content_type='application/json')
        with self.assertRaises(Problem) as ctx:
            json_object(request)
        self.assertEqual(ctx.exception.slug, 'malformed-request')

    def test_undecodable_bytes_are_malformed_request(self):
        request = RequestFactory().post('/api/x', data=b'\xff\xfe', content_type='application/json')
        with self.assertRaises(Problem) as ctx:
            json_object(request)
        self.assertEqual(ctx.exception.slug, 'malformed-request')


class ExceptionHandlerTest(TestCase):
    """PD-110: framework exceptions keep their status and get the generic slug of it."""

    def test_problem_exception_is_rendered_with_its_own_slug_detail_and_errors(self):
        errors = [body_error('email', 'This field is required.')]
        response = handle(Problem('validation-error', 'One or more fields are invalid.', errors), '/api/auth/login')
        assert_problem(response, 'validation-error', errors=errors)
        self.assertEqual(json.loads(response.content)['instance'], '/api/auth/login')

    def test_drf_validation_error_becomes_validation_error_with_items(self):
        response = handle(exceptions.ValidationError({'name': ['Too long']}))
        assert_problem(response, 'validation-error', errors=[{'pointer': '#/name', 'detail': 'Too long.'}])

    def test_drf_validation_error_without_a_field_points_at_the_root(self):
        response = handle(exceptions.ValidationError(['Broken']))
        assert_problem(response, 'validation-error', errors=[{'pointer': '#', 'detail': 'Broken.'}])

    def test_parse_error_is_malformed_request(self):
        assert_problem(handle(exceptions.ParseError('JSON parse error - Expecting value')), 'malformed-request')

    def test_parse_error_does_not_leak_the_exception_text(self):
        body = json.loads(handle(exceptions.ParseError('JSON parse error - Expecting value')).content)
        self.assertNotIn('Expecting', body['detail'])

    def test_method_not_allowed(self):
        assert_problem(handle(exceptions.MethodNotAllowed('PATCH')), 'method-not-allowed')

    def test_unsupported_media_type(self):
        assert_problem(handle(exceptions.UnsupportedMediaType('text/plain')), 'unsupported-media-type')

    def test_not_authenticated_and_authentication_failed_are_invalid_session(self):
        assert_problem(handle(exceptions.NotAuthenticated()), 'invalid-session')
        assert_problem(handle(exceptions.AuthenticationFailed()), 'invalid-session')

    def test_permission_denied_is_forbidden_for_drf_and_django(self):
        """Includes the CSRF failure of SessionAuthentication, which DRF raises as PermissionDenied."""
        assert_problem(handle(exceptions.PermissionDenied('CSRF Failed: token missing.')), 'forbidden')
        assert_problem(handle(DjangoPermissionDenied()), 'forbidden')

    def test_not_found_and_http404_are_not_found(self):
        assert_problem(handle(exceptions.NotFound()), 'not-found', detail='Resource not found.')
        assert_problem(handle(Http404('No Service matches the given query.')), 'not-found', detail='Resource not found.')

    def test_throttled_sends_retry_after_in_whole_seconds(self):
        response = handle(exceptions.Throttled(wait=41.2))
        assert_problem(response, 'too-many-requests')
        self.assertEqual(response['Retry-After'], '42')

    def test_throttled_without_wait_omits_retry_after(self):
        """PD-113"""
        response = handle(exceptions.Throttled())
        assert_problem(response, 'too-many-requests')
        self.assertFalse(response.has_header('Retry-After'))

    def test_other_client_api_exception_keeps_its_status_and_is_malformed_request(self):
        response = handle(exceptions.NotAcceptable())
        assert_problem(response, 'malformed-request', status=406)

    def test_unexpected_exception_is_internal_error_and_is_logged_with_traceback(self):
        with self.assertLogs('hairmatch.problems', level='ERROR') as logs:
            try:
                raise RuntimeError('secret internals')
            except RuntimeError as exc:
                response = handle(exc, '/api/reservations', 'POST')
        body = assert_problem(response, 'internal-error', detail='An unexpected error occurred.')
        self.assertNotIn('secret', json.dumps(body))
        self.assertEqual(len(logs.records), 1)
        record = logs.records[0]
        self.assertEqual(record.levelname, 'ERROR')
        self.assertIn('POST /api/reservations', record.getMessage())
        self.assertIsNotNone(record.exc_info)
        self.assertIn('secret internals', logs.output[0])  # the traceback is in the server log

    def test_api_exception_with_status_500_is_internal_error(self):
        with self.assertLogs('hairmatch.problems', level='ERROR'):
            response = handle(exceptions.APIException('boom'))
        assert_problem(response, 'internal-error')


@override_settings(DEBUG=False)
class ApiRoutesTest(TestCase):
    """PD-60 to PD-66, run with DEBUG off (the test runner's value) and on (production's)."""

    def setUp(self):
        self.client = APIClient()

    def check_unknown_route_is_a_problem(self):
        response = self.client.get('/api/does-not-exist?token=abc')
        body = assert_problem(response, 'not-found')
        self.assertEqual(body['instance'], '/api/does-not-exist')

    def test_unknown_route_debug_off(self):
        self.check_unknown_route_is_a_problem()

    @override_settings(DEBUG=True)
    def test_unknown_route_debug_on(self):
        self.check_unknown_route_is_a_problem()

    def test_unknown_route_with_a_route_prefix_and_a_deeper_path(self):
        assert_problem(self.client.get('/api/services/does/not/exist'), 'not-found')

    def test_bare_api_path_is_not_found(self):
        assert_problem(self.client.get('/api'), 'not-found')

    def test_unknown_route_ignores_the_method_and_the_csrf_check(self):
        client = Client(enforce_csrf_checks=True)
        for method in ('post', 'put', 'delete', 'patch'):
            with self.subTest(method=method):
                assert_problem(getattr(client, method)('/api/does-not-exist'), 'not-found')

    def test_unmatched_converter_is_not_found(self):
        """`<int:...>` does not match a word, so the URL falls through to the catch-all."""
        assert_problem(self.client.get('/api/hairdressers/abc'), 'not-found')

    def test_method_not_allowed_keeps_the_allow_header(self):
        response = self.client.patch('/api/auth/login', data='{}', content_type='application/json')
        assert_problem(response, 'method-not-allowed')
        allowed = {method.strip() for method in response['Allow'].split(',')}
        self.assertEqual(allowed, {'POST', 'OPTIONS'})
        self.assertNotIn('PATCH', allowed)

    def test_method_not_allowed_ignores_an_html_accept_header(self):
        response = self.client.patch('/api/auth/login', HTTP_ACCEPT='text/html')
        assert_problem(response, 'method-not-allowed')

    def test_unsupported_media_type(self):
        response = self.client.post('/api/users', data='{}', content_type='application/json')
        assert_problem(response, 'unsupported-media-type')

    def test_throttle_answers_429_with_retry_after(self):
        with patch.object(CepLookupThrottle, 'rate', '1/min'):
            first = self.client.get('/api/postal-codes/123')
            second = self.client.get('/api/postal-codes/123')
        self.assertEqual(first.status_code, 400)
        assert_problem(second, 'too-many-requests')
        self.assertGreater(int(second['Retry-After']), 0)

    def check_unhandled_exception_is_a_problem(self):
        with patch('users.views.lookup_cep', side_effect=RuntimeError('db password is hunter2')):
            with self.assertLogs('hairmatch.problems', level='ERROR') as logs:
                response = self.client.get('/api/postal-codes/69050750')
        body = assert_problem(response, 'internal-error', detail='An unexpected error occurred.')
        self.assertNotIn('hunter2', json.dumps(body))
        self.assertIn('GET /api/postal-codes/69050750', logs.records[0].getMessage())
        self.assertIn('hunter2', logs.output[0])
        self.assertIn('Traceback', logs.output[0])

    def test_unhandled_exception_debug_off(self):
        self.check_unhandled_exception_is_a_problem()

    @override_settings(DEBUG=True)
    def test_unhandled_exception_debug_on(self):
        self.check_unhandled_exception_is_a_problem()

    def test_cors_headers_are_kept_on_problems(self):
        response = self.client.get('/api/does-not-exist', HTTP_ORIGIN='http://localhost:8081')
        self.assertEqual(response['Access-Control-Allow-Origin'], 'http://localhost:8081')
        self.assertEqual(response['Access-Control-Allow-Credentials'], 'true')


class OutsideApiTest(TestCase):
    """PD-67: only /api/ changes."""

    @override_settings(DEBUG=False)
    def test_admin_is_untouched(self):
        response = self.client.get('/admin/', follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertNotEqual(response.get('Content-Type'), 'application/problem+json')

    @override_settings(DEBUG=False)
    def test_unknown_path_outside_api_keeps_the_django_404(self):
        response = self.client.get('/not-an-api-path')
        self.assertEqual(response.status_code, 404)
        self.assertNotEqual(response['Content-Type'], 'application/problem+json')


class NoResponseView(APIView):
    """A view that forgets to return a response: DRF asserts in finalize_response, outside its own handler."""

    def get(self, request):
        return None


class UnrenderableView(APIView):
    """A view whose data the JSON renderer cannot encode: it fails when Django renders the response."""

    def get(self, request):
        return Response({'value': object()})


urlpatterns = [
    path('api/no-response', NoResponseView.as_view()),
    path('api/unrenderable', UnrenderableView.as_view()),
    path('elsewhere/no-response', NoResponseView.as_view()),
]


@override_settings(ROOT_URLCONF='hairmatch.test_problems')
class EscapedExceptionTest(TestCase):
    """PD-64: an exception that DRF's handler never sees still answers in problem+json, with any DEBUG."""

    def setUp(self):
        self.client = APIClient(raise_request_exception=False)

    def check_is_an_internal_error_problem(self, url):
        with self.assertLogs('hairmatch.problems', level='ERROR') as logs:
            response = self.client.get(url)

        assert_problem(response, 'internal-error', detail='An unexpected error occurred.')
        self.assertIn(f'GET {url}', logs.records[0].getMessage())
        self.assertIsNotNone(logs.records[0].exc_info)

    def test_a_view_that_returns_nothing_debug_off(self):
        self.check_is_an_internal_error_problem('/api/no-response')

    @override_settings(DEBUG=True)
    def test_a_view_that_returns_nothing_debug_on(self):
        self.check_is_an_internal_error_problem('/api/no-response')

    def test_a_response_that_cannot_be_rendered_debug_off(self):
        self.check_is_an_internal_error_problem('/api/unrenderable')

    @override_settings(DEBUG=True)
    def test_a_response_that_cannot_be_rendered_debug_on(self):
        self.check_is_an_internal_error_problem('/api/unrenderable')

    def test_the_middleware_leaves_paths_outside_api_alone(self):
        middleware = ProblemDetailsMiddleware(lambda request: None)

        self.assertIsNone(middleware.process_exception(RequestFactory().get('/elsewhere/no-response'), RuntimeError()))
        self.assertIsNone(middleware.process_exception(RequestFactory().get('/admin/'), RuntimeError()))

    @override_settings(DEBUG=False)
    def test_a_path_outside_api_keeps_the_django_500(self):
        response = self.client.get('/elsewhere/no-response')

        self.assertEqual(response.status_code, 500)
        self.assertNotEqual(response['Content-Type'], 'application/problem+json')
