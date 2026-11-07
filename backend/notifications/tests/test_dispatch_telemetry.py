import json
from datetime import datetime, time, timezone as dt_timezone
from unittest.mock import patch

from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from opentelemetry.trace import SpanKind

from availability.models import Availability
from hairmatch import testing_telemetry
from notifications.dispatch import publish_alert
from notifications.models import Alert, PushDevice
from notifications.sns import SnsService
from reserve.models import Reserve
from service.models import Service
from users.models import Customer, Hairdresser

from .helpers import login, make_user

ARN = 'arn:aws:sns:us-east-2:123456789012:endpoint/GCM/hairmatch-dev-fcm/0a1b2c3d-secret-endpoint'
TOKEN = 'fcm-token-that-must-not-leak'
TITLE, BODY = 'Nova reserva', 'Ana reservou Corte para 20/10 às 09:00.'


def expected_publish(alert):
    fcm_message = {'message': {
        'notification': {'title': TITLE, 'body': BODY},
        'data': {'alert_id': str(alert.pk), 'kind': 'reservation-created'},
        'android': {'priority': 'high', 'notification': {'channel_id': 'default'}},
    }}
    message = {'default': BODY, 'GCM': json.dumps({'fcmV1Message': fcm_message})}
    return {'TargetArn': ARN, 'Message': json.dumps(message), 'MessageStructure': 'json'}


class PushCounterTests(testing_telemetry.TelemetryMixin, TestCase):
    """TEL-52, TEL-53, TEL-48: one count per attempt, and the SNS call as it was before."""

    def setUp(self):
        super().setUp()
        self.user = make_user('push@example.com', '5592900000010', 'hairdresser')
        self.device = PushDevice.objects.create(user=self.user, token=TOKEN, endpoint_arn=ARN)
        self.alert = Alert.objects.create(
            recipient=self.user, kind='reservation-created', title=TITLE, body=BODY, data={'reservation_id': 7},
        )
        client, self.stubber = testing_telemetry.stubbed_client('sns')
        service = SnsService(client)
        patcher = patch('notifications.dispatch.get_sns', return_value=service)
        patcher.start()
        self.addCleanup(patcher.stop)
        testing_telemetry.clear()

    def results(self):
        return sorted((attrs['outcome'], value) for attrs, value in self.points('hairmatch.push.results'))

    def test_a_delivered_push_counts_published_and_sends_the_same_request_as_before(self):
        self.stubber.add_response('publish', {'MessageId': 'm-1'}, expected_publish(self.alert))
        with self.stubber:
            publish_alert(self.alert.pk)
        self.stubber.assert_no_pending_responses()
        self.assertEqual(self.results(), [('published', 1)])

    def test_the_sns_span_has_no_arn_token_or_message_body(self):
        self.stubber.add_response('publish', {'MessageId': 'm-1'}, expected_publish(self.alert))
        with self.stubber:
            publish_alert(self.alert.pk)
        span = self.span('SNS.Publish')
        self.assertEqual(span.kind, SpanKind.CLIENT)
        text = repr(dict(span.attributes)) + span.name + repr(span.events) + repr(span.status.description)
        for secret in ('secret-endpoint', 'arn:aws', TOKEN, 'Ana reservou', 'GCM'):
            self.assertNotIn(secret, text)
        self.assertFalse([key for key in span.attributes if key.startswith('messaging.')])

    def test_a_disabled_endpoint_counts_endpoint_gone_and_removes_the_phone(self):
        self.stubber.add_client_error('publish', service_error_code='EndpointDisabled', http_status_code=400)
        self.stubber.add_response('delete_endpoint', {})
        with self.stubber, self.assertLogs('notifications.sns', 'WARNING'):
            publish_alert(self.alert.pk)
        self.assertEqual(self.results(), [('endpoint_gone', 1)])
        self.assertFalse(PushDevice.objects.exists())

    def test_sns_down_counts_unavailable_and_keeps_the_phone(self):
        self.stubber.add_client_error('publish', service_error_code='InternalError', http_status_code=500)
        with self.stubber, self.assertLogs('notifications.sns', 'WARNING'):
            publish_alert(self.alert.pk)
        self.assertEqual(self.results(), [('unavailable', 1)])
        self.assertTrue(PushDevice.objects.exists())

    def test_a_failure_outside_the_device_loop_counts_error(self):
        with patch('notifications.dispatch.PushDevice') as devices:
            devices.objects.filter.side_effect = RuntimeError('database gone')
            with self.assertLogs('notifications.dispatch', 'WARNING'):
                publish_alert(self.alert.pk)
        self.assertEqual(self.results(), [('error', 1)])

    def test_an_alert_without_devices_counts_nothing(self):
        PushDevice.objects.all().delete()
        publish_alert(self.alert.pk)
        self.assertEqual(self.results(), [])


class ReserveTraceTests(testing_telemetry.TelemetryMixin, TransactionTestCase):
    """TEL-22: request, queries and SNS.Publish of a reservation share one trace_id.

    A TransactionTestCase because the push goes out in `on_commit`: in a TestCase it would only run after the response,
    outside the request, and would prove nothing about the trace.
    """

    START = datetime(2030, 3, 4, 14, 0, tzinfo=dt_timezone.utc)

    def setUp(self):
        super().setUp()
        self.customer_user = make_user('customer@example.com', '5592900000011', 'customer')
        Customer.objects.create(user=self.customer_user, cpf='12345678901')
        hairdresser_user = make_user('hairdresser@example.com', '5592900000012', 'hairdresser')
        hairdresser = Hairdresser.objects.create(user=hairdresser_user, cnpj='12345678901212')
        self.service = Service.objects.create(name='Corte', description='Corte', price=50, duration=60, hairdresser=hairdresser)
        self.hairdresser = hairdresser
        Availability.objects.create(
            hairdresser=hairdresser, weekday='monday', start_time=time(9), end_time=time(17),
            break_start=time(12), break_end=time(13),
        )
        PushDevice.objects.create(user=hairdresser_user, token=TOKEN, endpoint_arn=ARN)
        client, self.stubber = testing_telemetry.stubbed_client('sns')
        patcher = patch('notifications.dispatch.get_sns', return_value=SnsService(client))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_the_reservation_request_its_queries_and_the_sns_publish_share_the_trace(self):
        self.stubber.add_response('publish', {'MessageId': 'm-1'})
        testing_telemetry.clear()

        with self.stubber:
            response = login(self.customer_user).post(
                reverse('reservation_collection'),
                data=json.dumps({
                    'hairdresser': self.hairdresser.id, 'service': self.service.id, 'start_time': self.START.isoformat(),
                }),
                content_type='application/json',
            )

        # Read before any other query of the test, which would be a trace of its own.
        recorded = self.spans()
        self.assertEqual(response.status_code, 201)
        self.stubber.assert_no_pending_responses()
        self.assertEqual(Reserve.objects.count(), 1)
        request_span = next(s for s in recorded if s.kind == SpanKind.SERVER)
        trace_id = request_span.context.trace_id
        publish = self.span('SNS.Publish')
        queries = [s for s in recorded if s.kind == SpanKind.CLIENT and s.attributes.get('db.system') == 'postgresql']
        self.assertTrue(queries)
        self.assertEqual(publish.context.trace_id, trace_id)
        self.assertEqual({s.context.trace_id for s in recorded}, {trace_id})
