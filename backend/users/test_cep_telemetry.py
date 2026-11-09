import json
from unittest.mock import patch

import requests
from django.core.cache import cache
from django.test import TestCase
from opentelemetry.trace import SpanKind, StatusCode

from hairmatch import testing_telemetry
from users.cep_lookup import CepNotFound, CepServiceUnavailable, lookup_cep

CEP = '69057123'
VIACEP_OK = {'logradouro': 'Rua Teste', 'bairro': 'Centro', 'localidade': 'Manaus', 'uf': 'AM'}
BRASILAPI_OK = {'street': 'Rua Teste', 'neighborhood': 'Centro', 'city': 'Manaus', 'state': 'AM'}


def answer(request, status, body=None):
    response = requests.Response()
    response.status_code = status
    response._content = json.dumps(body if body is not None else {}).encode()
    response.url = request.url
    response.request = request
    return response


class CepTelemetryTests(testing_telemetry.TelemetryMixin, TestCase):
    """TEL-19, TEL-57: the providers are CLIENT spans without the CEP, and each lookup is counted by where it was answered."""

    def setUp(self):
        super().setUp()
        cache.clear()
        self.sent = []

    def providers(self, viacep, brasilapi):
        """Replaces the network below `requests`, so its instrumentation still runs. Each answer is (status, body) or an exception."""
        answers = {'viacep.com.br': viacep, 'brasilapi.com.br': brasilapi}

        def send(adapter, request, **kwargs):
            self.sent.append(request.url)
            host = request.url.split('/')[2]
            result = answers[host]
            if isinstance(result, Exception):
                raise result
            return answer(request, *result)

        return patch('requests.adapters.HTTPAdapter.send', send)

    def lookups(self):
        return sorted((a['source'], value) for a, value in self.points('hairmatch.cep.lookups'))

    def test_the_provider_call_is_a_client_span_with_method_host_and_status_and_no_cep(self):
        with self.providers((200, VIACEP_OK), (200, BRASILAPI_OK)):
            lookup_cep(CEP)
        (span,) = [s for s in self.spans() if s.kind == SpanKind.CLIENT and 'http.request.method' in s.attributes]
        self.assertEqual(span.attributes['http.request.method'], 'GET')
        self.assertEqual(span.attributes['server.address'], 'viacep.com.br')
        self.assertEqual(span.attributes['http.response.status_code'], 200)
        self.assertNotIn(CEP, repr(dict(span.attributes)) + span.name + repr(span.events))

    def test_a_failing_provider_leaves_no_cep_in_the_span_nor_in_the_log(self):
        down = requests.ConnectionError(
            f"HTTPSConnectionPool(host='viacep.com.br', port=443): Max retries exceeded with url: /ws/{CEP}/json/ (Caused by X)"
        )
        with self.providers(down, (200, BRASILAPI_OK)), self.assertLogs('users.cep_lookup', 'WARNING') as logs:
            lookup_cep(CEP)
        self.assertEqual(logs.output, ['WARNING:users.cep_lookup:CEP provider viacep failed: connection error: ConnectionError'])
        failed = next(s for s in self.spans() if s.attributes.get('server.address') == 'viacep.com.br')
        self.assertEqual(failed.status.status_code, StatusCode.ERROR)
        self.assertNotIn(CEP, repr(failed.status.description) + repr(dict(failed.attributes)) + repr(failed.events))
        for record in self.log_records():
            self.assertNotIn(CEP, str(record.body) + repr(dict(record.attributes or {})))

    def test_each_source_is_counted_once_per_lookup(self):
        with self.providers((200, VIACEP_OK), (200, BRASILAPI_OK)):
            lookup_cep(CEP)
            lookup_cep(CEP)  # the cache
        self.assertEqual(self.lookups(), [('cache', 1), ('viacep', 1)])

    def test_brasilapi_is_counted_when_viacep_is_down(self):
        with self.providers(requests.Timeout(), (200, BRASILAPI_OK)), self.assertLogs('users.cep_lookup', 'WARNING'):
            lookup_cep(CEP)
        self.assertEqual(self.lookups(), [('brasilapi', 1)])

    def test_not_found_and_unavailable_are_counted(self):
        with self.providers((200, {'erro': True}), (404, {})):
            with self.assertRaises(CepNotFound):
                lookup_cep(CEP)
        cache.clear()
        with self.providers(requests.Timeout(), requests.Timeout()), self.assertLogs('users.cep_lookup', 'WARNING'):
            with self.assertRaises(CepServiceUnavailable):
                lookup_cep(CEP)
        self.assertEqual(self.lookups(), [('not_found', 1), ('unavailable', 1)])

    def test_an_invalid_cep_is_not_a_lookup(self):
        from users.cep_lookup import InvalidCep

        with self.assertRaises(InvalidCep):
            lookup_cep('123')
        self.assertEqual(self.lookups(), [])
