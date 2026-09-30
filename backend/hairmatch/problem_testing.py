"""Test helper: asserts that a response is a well-formed problem+json of the catalog."""
import json
import unittest

from hairmatch.problems import CATALOG

_case = unittest.TestCase()


def assert_problem(response, slug, detail=None, errors=None, status=None):
    """
    Checks the RFC 9457 contract (PD-01 to PD-06) and returns the parsed body.
    `detail` and `errors`, when given, must match exactly; `status` defaults to the catalog's.
    """
    expected_status, title = CATALOG[slug]
    expected_status = status or expected_status
    _case.assertEqual(response.status_code, expected_status, response.content)
    _case.assertEqual(response['Content-Type'], 'application/problem+json')
    body = json.loads(response.content)

    expected_members = {'type', 'title', 'status', 'detail', 'instance'}
    if slug == 'validation-error':
        expected_members.add('errors')
    _case.assertEqual(set(body), expected_members)
    _case.assertEqual(body['type'], f'https://hairmatch.app/problems/{slug}')
    _case.assertEqual(body['title'], title)
    _case.assertEqual(body['status'], expected_status)
    _case.assertTrue(body['detail'].endswith('.'), body['detail'])
    if detail is not None:
        _case.assertEqual(body['detail'], detail)
    if errors is not None:
        _case.assertEqual(body['errors'], errors)
    return body
