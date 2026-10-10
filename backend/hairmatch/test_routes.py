import importlib
import re

from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import get_resolver
from django.urls.resolvers import URLPattern, URLResolver

import hairmatch.urls

# The Route Table of .specs/features/api-restful-routes/spec.md (RT-01 to RT-49, plus RT-84 and RT-85 from email-confirmation
# and RT-86 and RT-87 from customer-rating, and RT-88 and RT-89 from account-settings), one (method, route)
# pair per row.
# `{id}` is an integer segment and `{cep}` is free text.
ROUTE_TABLE = {
    ('POST', 'users'),                                            # RT-01
    ('GET', 'auth/session'),                                      # RT-02
    ('POST', 'auth/login'),                                       # RT-03
    ('POST', 'auth/logout'),                                      # RT-04
    ('POST', 'auth/refresh'),                                     # RT-05
    ('POST', 'auth/google'),                                      # RT-06
    ('PUT', 'users/me/password'),                                 # RT-07
    ('GET', 'users/me'),                                          # RT-08
    ('PATCH', 'users/me'),                                        # RT-09
    ('DELETE', 'users/me'),                                       # RT-10
    ('GET', 'search'),                                            # RT-12
    ('GET', 'customers/me/home'),                                 # RT-13
    ('GET', 'home'),                                              # RT-14
    ('GET', 'hairdressers/{id}'),                                 # RT-15
    ('POST', 'hairdressers/description-drafts'),                  # RT-16
    ('GET', 'postal-codes/{cep}'),                                # RT-17
    ('GET', 'preferences'),                                       # RT-18
    ('GET', 'users/{id}/preferences'),                            # RT-19
    ('GET', 'preferences/{id}/users'),                            # RT-20
    ('PUT', 'users/me/preferences/{id}'),                         # RT-21
    ('DELETE', 'users/me/preferences/{id}'),                      # RT-22
    ('POST', 'reviews'),                                          # RT-23
    ('GET', 'hairdressers/{id}/reviews'),                         # RT-24
    ('PUT', 'reviews/{id}'),                                      # RT-25
    ('DELETE', 'reviews/{id}'),                                   # RT-26
    ('POST', 'availabilities'),                                   # RT-27
    ('POST', 'hairdressers/{id}/availabilities'),                 # RT-28
    ('PUT', 'hairdressers/{id}/availabilities'),                  # RT-29
    ('GET', 'hairdressers/{id}/availabilities'),                  # RT-30
    ('PATCH', 'availabilities/{id}'),                             # RT-31
    ('DELETE', 'availabilities/{id}'),                            # RT-32
    ('POST', 'agenda'),                                           # RT-33
    ('GET', 'agenda'),                                            # RT-34
    ('GET', 'hairdressers/{id}/agenda'),                          # RT-35
    ('DELETE', 'agenda/{id}'),                                    # RT-36
    ('POST', 'services'),                                         # RT-37
    ('GET', 'services'),                                          # RT-38
    ('GET', 'services/{id}'),                                     # RT-39
    ('GET', 'hairdressers/{id}/services'),                        # RT-40
    ('PUT', 'services/{id}'),                                     # RT-41
    ('DELETE', 'services/{id}'),                                  # RT-42
    ('GET', 'reservations/{id}'),                                 # RT-43
    ('POST', 'reservations'),                                     # RT-44
    ('GET', 'reservations'),                                      # RT-45
    ('GET', 'customers/{id}/reservations'),                       # RT-46
    ('DELETE', 'reservations/{id}'),                              # RT-47
    ('GET', 'hairdressers/{id}/available-slots'),                 # RT-48
    ('POST', 'chatbot/webhook'),                                  # RT-49
    ('POST', 'auth/email-confirmations'),                         # RT-84
    ('POST', 'auth/confirmation-codes'),                          # RT-85
    ('POST', 'customer-ratings'),                                 # RT-86
    ('GET', 'customers/{id}/ratings'),                            # RT-87
    ('PUT', 'users/me/profile-picture'),                          # RT-88
    ('DELETE', 'users/me/profile-picture'),                       # RT-89
}

# RT-54: the only singular or non-plural segments the table allows.
SINGULAR_SEGMENTS = {
    'agenda', 'home', 'search', 'me', 'password', 'profile-picture', 'session', 'chatbot', 'webhook',
    'auth', 'login', 'logout', 'refresh', 'google',
    'description-drafts', 'available-slots', 'postal-codes',
}


def _walk(patterns, prefix=''):
    for pattern in patterns:
        route = prefix + str(pattern.pattern)
        if isinstance(pattern, URLResolver):
            yield from _walk(pattern.url_patterns, route)
        elif isinstance(pattern, URLPattern):
            yield route, pattern.callback


def _normalize(route):
    route = re.sub(r'<int:[a-z_]+>', '{id}', route)
    return re.sub(r'<str:[a-z_]+>', '{cep}', route)


def api_routes():
    """Every (method, route) the URLconf exposes under /api/, without the catch-all, HEAD and OPTIONS."""
    found = set()
    for route, callback in _walk(get_resolver().url_patterns):
        if not route.startswith('api/') or not hasattr(callback, 'cls'):
            continue
        methods = set(callback.cls().allowed_methods) - {'OPTIONS', 'HEAD'}
        found |= {(method, _normalize(route[len('api/'):])) for method in methods}
    return found


class RouteTableTests(SimpleTestCase):
    def test_api_exposes_exactly_the_route_table(self):
        """RT-50: no route beyond the table, and none of it missing."""
        found = api_routes()
        self.assertEqual(sorted(ROUTE_TABLE - found), [], 'in the table but not routed')
        self.assertEqual(sorted(found - ROUTE_TABLE), [], 'routed but not in the table')

    def test_paths_use_only_lowercase_digits_dash_and_slash_without_trailing_slash(self):
        """RT-54: lowercase, digits, `-` and `/`, no trailing slash, plural collections and no verbs."""
        for _, route in api_routes():
            with self.subTest(route=route):
                self.assertRegex(re.sub(r'\{(id|cep)\}', '', route), r'^[a-z0-9/-]+$')
                self.assertFalse(route.endswith('/'))
                for segment in route.split('/'):
                    if segment in ('{id}', '{cep}'):
                        continue
                    self.assertTrue(
                        segment.endswith('s') or segment in SINGULAR_SEGMENTS,
                        f'{segment!r} is neither a plural collection nor a listed exception',
                    )


class RouteBehaviorTests(TestCase):
    def assert_problem(self, response, status, slug):
        self.assertEqual(response.status_code, status)
        self.assertEqual(response['Content-Type'], 'application/problem+json')
        self.assertEqual(response.json()['type'], f'https://hairmatch.app/problems/{slug}')

    def test_old_paths_answer_404_not_found(self):
        """RT-52: a path that left the table is a route that does not exist."""
        old = [
            ('get', '/api/service/list'), ('get', '/api/user/authenticated'), ('post', '/api/auth/register'),
            ('get', '/api/auth/user'), ('put', '/api/auth/change-password'), ('get', '/api/user/search'),
            ('get', '/api/customer/home'), ('get', '/api/hairdresser/1'), ('get', '/api/address/cep/69057000'),
            ('post', '/api/reserve/slots/1'), ('post', '/api/preferences/assign/cookie/1'),
            ('post', '/api/chatbot/test'),
        ]
        for method, path in old:
            with self.subTest(path=path):
                self.assert_problem(getattr(self.client, method)(path), 404, 'not-found')

    def test_wrong_method_answers_405_with_the_allow_header_of_the_path(self):
        """RT-53: `/api/services/{id}` lists GET, PUT and DELETE, and POST is not one of them."""
        response = self.client.post('/api/services/1')
        self.assert_problem(response, 405, 'method-not-allowed')
        # HEAD comes with GET.
        self.assertEqual(sorted(response['Allow'].split(', ')), ['DELETE', 'GET', 'HEAD', 'OPTIONS', 'PUT'])

    def test_login_is_post_only(self):
        """RT-50: the old `GET /api/auth/login` (a session probe in the same view) is gone."""
        response = self.client.get('/api/auth/login')
        self.assert_problem(response, 405, 'method-not-allowed')
        self.assertEqual(sorted(response['Allow'].split(', ')), ['OPTIONS', 'POST'])

    def test_trailing_slash_is_not_redirected(self):
        """RT-80."""
        self.assert_problem(self.client.get('/api/services/'), 404, 'not-found')

    def test_non_integer_id_answers_404(self):
        """RT-81."""
        self.assert_problem(self.client.get('/api/services/abc'), 404, 'not-found')


class AdminRouteTests(SimpleTestCase):
    """The Django admin is only mounted with DEBUG; the test runner runs with DEBUG=False."""

    def _route_prefixes_with_debug(self, debug):
        with override_settings(DEBUG=debug):
            module = importlib.reload(hairmatch.urls)
        self.addCleanup(importlib.reload, hairmatch.urls)
        return [str(pattern.pattern) for pattern in module.urlpatterns]

    def test_admin_is_not_routed_without_debug(self):
        self.assertEqual(self.client.get('/admin/').status_code, 404)
        self.assertEqual(self.client.get('/admin/login/').status_code, 404)

    def test_admin_is_mounted_only_when_debug_is_on(self):
        self.assertNotIn('admin/', self._route_prefixes_with_debug(False))
        self.assertIn('admin/', self._route_prefixes_with_debug(True))
