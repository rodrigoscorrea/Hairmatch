from django.test import SimpleTestCase
from django.test import RequestFactory

from hairmatch import testing_telemetry
from hairmatch.problems import problem_response


class ProblemCounterTests(testing_telemetry.TelemetryMixin, SimpleTestCase):
    """TEL-50: each problem response adds 1, labelled with its slug and status."""

    def counted(self):
        return sorted((attrs['slug'], attrs['status'], value) for attrs, value in self.points('hairmatch.problems'))

    def test_an_unknown_route_counts_not_found_404(self):
        response = self.client.get('/api/does-not-exist')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.counted(), [('not-found', 404, 1)])

    def test_two_responses_of_the_same_slug_add_up(self):
        self.client.get('/api/nope-1')
        self.client.get('/api/nope-2')
        self.assertEqual(self.counted(), [('not-found', 404, 2)])

    def test_the_status_label_is_the_one_of_the_response_not_the_catalog(self):
        request = RequestFactory().get('/api/x')
        response = problem_response(request, 'malformed-request', 'x', status=413)
        self.assertEqual(response.status_code, 413)
        self.assertEqual(self.counted(), [('malformed-request', 413, 1)])

    def test_the_path_never_becomes_a_label(self):
        self.client.get('/api/users/12345/secret')
        (attrs, _) = self.points('hairmatch.problems')[0]
        self.assertEqual(set(attrs), {'slug', 'status'})
