import re
import uuid
from unittest import mock

from django.test import SimpleTestCase
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import SpanKind, Status, StatusCode

from hairmatch import otel

ARN = 'arn:aws:sns:us-east-2:000000000000:endpoint/GCM/hairmatch-dev-fcm/6f1c8e0a-aaaa-bbbb-cccc-1234567890ab'


class SanitizerTests(SimpleTestCase):
    def setUp(self):
        self.exporter = InMemorySpanExporter()
        provider = TracerProvider()
        provider.add_span_processor(otel.SanitizingSpanProcessor(SimpleSpanProcessor(self.exporter)))
        self.tracer = provider.get_tracer('test')

    def one(self):
        (span,) = self.exporter.get_finished_spans()
        return span

    def test_forbidden_attributes_are_removed(self):
        """TEL-47."""
        forbidden = {
            'url.query': 'q=ana@example.com', 'url.full': 'https://viacep.com.br/ws/69000000/json/',
            'url.path': '/api/postal-codes/69000000', 'http.url': 'http://x/69000000', 'http.target': '/x?cep=1',
            'client.address': '10.0.0.8', 'enduser.id': '7', 'http.request.header.cookie': 'jwt=abc',
            'http.request.header.authorization': 'Bearer x', 'http.response.header.set-cookie': 'a=b',
            'http.user_agent': 'curl', 'user_agent.original': 'curl', 'http.client_ip': '1.2.3.4',
        }
        kept = {'http.route': 'api/search', 'http.request.method': 'GET', 'http.response.status_code': 200,
                'server.address': 'viacep.com.br', 'db.statement': 'SELECT %s'}
        with self.tracer.start_as_current_span('GET api/search', attributes={**forbidden, **kept}):
            pass
        self.assertEqual(dict(self.one().attributes), kept)

    def test_messaging_attributes_are_removed(self):
        """TEL-48: the SNS extension would put the endpoint ARN in them."""
        with self.tracer.start_as_current_span('x', attributes={
            'messaging.system': 'aws.sns', 'messaging.destination': ARN, 'messaging.destination.name': ARN, 'rpc.method': 'Publish',
        }):
            pass
        self.assertEqual(dict(self.one().attributes), {'rpc.method': 'Publish'})

    def test_sns_span_is_renamed_after_service_and_operation_and_is_a_client_span(self):
        """TEL-18, TEL-48."""
        with self.tracer.start_as_current_span(f'{ARN.split(":")[-1]} send', kind=SpanKind.PRODUCER, attributes={
            'rpc.system': 'aws-api', 'rpc.service': 'SNS', 'rpc.method': 'Publish', 'messaging.destination': ARN,
        }):
            pass
        span = self.one()
        self.assertEqual(span.name, 'SNS.Publish')
        self.assertEqual(span.kind, SpanKind.CLIENT)
        self.assertNotIn('6f1c8e0a', repr(span.attributes) + span.name)

    def test_arn_in_any_text_becomes_a_marker(self):
        with self.tracer.start_as_current_span('x', attributes={'note': f'to {ARN}'}) as span:
            span.set_status(Status(StatusCode.ERROR, f'An error occurred when calling Publish on {ARN}'))
        out = self.one()
        self.assertEqual(out.attributes['note'], 'to [arn]')
        self.assertEqual(out.status.description, 'An error occurred when calling Publish on [arn]')

    def test_exception_event_and_status_are_redacted(self):
        """TEL-86."""
        with self.assertRaises(ValueError):
            with self.tracer.start_as_current_span('work', record_exception=False, set_status_on_exception=False) as span:
                try:
                    raise ValueError('duplicate key ana@example.com cpf 123.456.789-09 phone (92) 99999-9999')
                except ValueError as exc:
                    span.record_exception(exc)
                    span.set_status(Status(StatusCode.ERROR, str(exc)))
                    raise
        out = self.one()
        (event,) = out.events
        self.assertEqual(event.name, 'exception')
        self.assertEqual(event.attributes['exception.type'], 'ValueError')
        self.assertEqual(event.attributes['exception.message'], 'duplicate key [email] cpf [cpf] phone [telefone]')
        self.assertIn('ValueError: duplicate key [email] cpf [cpf] phone [telefone]', event.attributes['exception.stacktrace'])
        self.assertNotIn('ana@example.com', event.attributes['exception.stacktrace'])
        self.assertEqual(out.status.status_code, StatusCode.ERROR)
        self.assertEqual(out.status.description, 'duplicate key [email] cpf [cpf] phone [telefone]')

    def test_url_in_an_exception_message_keeps_the_host_and_loses_the_path(self):
        """A CEP lives in a URL path, and the pattern for personal data does not cover 8 digits."""
        with self.tracer.start_as_current_span('GET') as span:
            span.record_exception(ConnectionError('HTTPSConnectionPool(host=viacep.com.br): https://viacep.com.br/ws/69000000/json/'))
        (event,) = self.one().events
        self.assertNotIn('69000000', event.attributes['exception.message'])
        self.assertIn('https://viacep.com.br/[path]', event.attributes['exception.message'])

    def test_string_attributes_and_lists_are_redacted_and_numbers_pass(self):
        with self.tracer.start_as_current_span('x', attributes={
            'a': 'mail ana@example.com', 'b': ['ok', 'cpf 12345678909'], 'c': 7, 'd': True, 'e': 1.5,
        }):
            pass
        attributes = dict(self.one().attributes)
        self.assertEqual(attributes['a'], 'mail [email]')
        self.assertEqual(tuple(attributes['b']), ('ok', 'cpf [cpf]'))
        self.assertEqual((attributes['c'], attributes['d'], attributes['e']), (7, True, 1.5))

    def test_span_name_is_redacted(self):
        with self.tracer.start_as_current_span('lookup ana@example.com'):
            pass
        self.assertEqual(self.one().name, 'lookup [email]')

    def test_identity_timing_and_links_are_preserved(self):
        with self.tracer.start_as_current_span('parent') as parent:
            with self.tracer.start_as_current_span('child', kind=SpanKind.CLIENT) as child:
                pass
        by_name = {s.name: s for s in self.exporter.get_finished_spans()}
        out = by_name['child']
        self.assertEqual(out.context.trace_id, child.get_span_context().trace_id)
        self.assertEqual(out.context.span_id, child.get_span_context().span_id)
        self.assertEqual(out.parent.span_id, parent.get_span_context().span_id)
        self.assertEqual(out.kind, SpanKind.CLIENT)
        self.assertEqual((out.start_time, out.end_time), (child.start_time, child.end_time))
        self.assertIs(out.resource, child.resource)
        self.assertEqual(out.instrumentation_scope.name, 'test')

    def test_status_without_description_is_unchanged(self):
        with self.tracer.start_as_current_span('x') as span:
            span.set_status(Status(StatusCode.OK))
        self.assertEqual(self.one().status.status_code, StatusCode.OK)

    def test_span_that_cannot_be_sanitized_is_dropped_not_exported_raw(self):
        with mock.patch.object(otel, 'sanitize_span', side_effect=RuntimeError('boom')):
            with self.tracer.start_as_current_span('x', attributes={'a': 'ana@example.com'}):
                pass
        self.assertEqual(self.exporter.get_finished_spans(), ())

    def test_shutdown_and_force_flush_reach_the_next_processor(self):
        inner = mock.Mock()
        inner.force_flush.return_value = True
        processor = otel.SanitizingSpanProcessor(inner)
        self.assertTrue(processor.force_flush(10))
        processor.shutdown()
        inner.force_flush.assert_called_once_with(10)
        inner.shutdown.assert_called_once_with()


class ResourceTests(SimpleTestCase):
    """TEL-29, TEL-30, TEL-31."""

    def attrs(self, environ):
        return dict(otel.build_resource(environ).attributes)

    def test_service_name_comes_from_otel_service_name(self):
        self.assertEqual(self.attrs({'OTEL_SERVICE_NAME': 'api-staging'})['service.name'], 'api-staging')

    def test_service_name_is_hairmatch_api_when_empty_or_absent(self):
        self.assertEqual(self.attrs({})['service.name'], 'hairmatch-api')
        self.assertEqual(self.attrs({'OTEL_SERVICE_NAME': ''})['service.name'], 'hairmatch-api')
        self.assertEqual(self.attrs({'OTEL_SERVICE_NAME': '  '})['service.name'], 'hairmatch-api')

    def test_service_name_can_also_come_from_the_resource_attributes(self):
        self.assertEqual(self.attrs({'OTEL_RESOURCE_ATTRIBUTES': 'service.name=from-attrs'})['service.name'], 'from-attrs')
        both = {'OTEL_SERVICE_NAME': 'wins', 'OTEL_RESOURCE_ATTRIBUTES': 'service.name=loses'}
        self.assertEqual(self.attrs(both)['service.name'], 'wins')

    def test_version_and_environment_come_from_the_resource_attributes(self):
        env = {'OTEL_RESOURCE_ATTRIBUTES': 'service.version=1.4.2,deployment.environment.name=staging'}
        attributes = self.attrs(env)
        self.assertEqual(attributes['service.version'], '1.4.2')
        self.assertEqual(attributes['deployment.environment.name'], 'staging')

    def test_version_and_environment_are_dev_when_absent_or_empty(self):
        for env in ({}, {'OTEL_RESOURCE_ATTRIBUTES': ''}, {'OTEL_RESOURCE_ATTRIBUTES': 'service.version=,deployment.environment.name='}):
            attributes = self.attrs(env)
            self.assertEqual((attributes['service.version'], attributes['deployment.environment.name']), ('dev', 'dev'))

    def test_instance_id_is_a_uuid_and_differs_between_processes(self):
        first, second = self.attrs({})['service.instance.id'], self.attrs({})['service.instance.id']
        self.assertNotEqual(first, second)
        self.assertEqual(uuid.UUID(first).hex, first)

    def test_malformed_attribute_entries_are_ignored(self):
        attributes = self.attrs({'OTEL_RESOURCE_ATTRIBUTES': 'novalue,=x,service.version=2'})
        self.assertEqual(attributes['service.version'], '2')
        self.assertNotIn('novalue', attributes)

    def test_sdk_attributes_are_kept(self):
        self.assertEqual(self.attrs({})['telemetry.sdk.language'], 'python')
