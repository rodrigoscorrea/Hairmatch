from unittest.mock import patch

from django.test import TransactionTestCase
from opentelemetry.trace import SpanKind

from hairmatch import testing_telemetry
from notifications.tests.test_dispatch_telemetry import ReserveFixture
from reserve.models import Reserve


def create_new_reserve(*args):
    # Imported when used: reserve.views first in the process hits a circular import between the serializers.
    from reserve.views import create_new_reserve as create

    return create(*args)


class ReserveTelemetryTests(ReserveFixture, TransactionTestCase):
    """TEL-28, TEL-51, TEL-41, TEL-42."""

    def counted(self):
        return sorted((attrs['channel'], value) for attrs, value in self.points('hairmatch.reserves.created'))

    def test_the_request_span_carries_the_two_ids_as_integers(self):
        self.stubber.add_response('publish', {'MessageId': 'm-1'})
        with self.stubber:
            response = self.post_reservation()
        recorded = self.spans()
        self.assertEqual(response.status_code, 201)
        request_span = next(s for s in recorded if s.kind == SpanKind.SERVER)
        reserve = Reserve.objects.get()
        self.assertEqual(request_span.attributes['hairmatch.reserve_id'], reserve.pk)
        self.assertEqual(request_span.attributes['hairmatch.hairdresser_id'], self.hairdresser.pk)
        self.assertIsInstance(request_span.attributes['hairmatch.reserve_id'], int)
        self.assertIsInstance(request_span.attributes['hairmatch.hairdresser_id'], int)

    def test_a_committed_reservation_by_the_app_counts_once_with_channel_app(self):
        self.stubber.add_response('publish', {'MessageId': 'm-1'})
        with self.stubber:
            self.post_reservation()
        self.assertEqual(self.counted(), [('app', 1)])

    def test_a_reservation_that_is_refused_counts_nothing(self):
        self.stubber.add_response('publish', {'MessageId': 'm-1'})
        with self.stubber:
            self.post_reservation()
        testing_telemetry.clear()
        response = self.post_reservation()  # the same slot, now taken
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.counted(), [])

    def test_a_rollback_counts_nothing_and_adds_no_span_attributes(self):
        with patch('reserve.views.Agenda.objects.create', side_effect=RuntimeError('disk on fire')):
            response = self.post_reservation()
        recorded = self.spans()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(Reserve.objects.count(), 0)
        self.assertEqual(self.counted(), [])
        request_span = next(s for s in recorded if s.kind == SpanKind.SERVER)
        self.assertNotIn('hairmatch.reserve_id', request_span.attributes)

    def test_a_chatbot_reservation_counts_once_with_channel_whatsapp(self):
        self.stubber.add_response('publish', {'MessageId': 'm-1'})
        with self.stubber:
            result = create_new_reserve(self.customer.id, self.service.id, self.hairdresser.id, self.START)
        self.assertTrue(result['success'])
        self.assertEqual(self.counted(), [('whatsapp', 1)])

    def test_an_unexpected_error_in_the_chatbot_reservation_logs_only_the_exception_type(self):
        with patch('reserve.views.Reserve.objects.create', side_effect=RuntimeError('Maria 5592999990000 disse oi')):
            with self.assertLogs('reserve.views', 'ERROR') as logs:
                result = create_new_reserve(self.customer.id, self.service.id, self.hairdresser.id, self.START)
        self.assertIn('error', result)
        self.assertEqual(logs.output, ['ERROR:reserve.views:create_new_reserve failed: RuntimeError'])
        self.assertEqual(self.counted(), [])
