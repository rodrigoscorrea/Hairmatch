from unittest.mock import patch

from django.db import transaction
from django.test import TestCase

from notifications.dispatch import delete_endpoints, notify, publish_alert
from notifications.messages import Message
from notifications.models import Alert, PushDevice
from notifications.sns import get_sns

from .helpers import make_user

TOKEN_1, TOKEN_2 = 'secret-token-1', 'secret-token-2'


class Boom(Exception):
    pass


class DispatchTestCase(TestCase):
    def setUp(self):
        self.recipient = make_user('recipient@example.com', '5592900000001', 'hairdresser')
        self.author = make_user('author@example.com', '5592900000002')
        self.sns = get_sns()
        self.fake = self.sns.client

    def register(self, user, token):
        return PushDevice.objects.create(user=user, token=token, endpoint_arn=self.sns.create_endpoint(token))

    def message(self, recipient=None):
        return Message(
            recipient=recipient or self.recipient, kind='reservation-created', title='Nova reserva',
            body='Ana reservou Corte para 20/10 às 09:00.', data={'reservation_id': 7},
        )


class NotifyTest(DispatchTestCase):
    def test_it_saves_one_unread_alert_with_the_catalog_fields(self):
        """NOTIF-19"""
        with self.captureOnCommitCallbacks(execute=True):
            alert = notify(self.message(), actor=self.author)

        saved = Alert.objects.get()
        self.assertEqual(saved.pk, alert.pk)
        self.assertEqual(
            (saved.recipient, saved.kind, saved.title, saved.body, saved.data, saved.read_at),
            (self.recipient, 'reservation-created', 'Nova reserva', 'Ana reservou Corte para 20/10 às 09:00.',
             {'reservation_id': 7}, None),
        )

    def test_it_publishes_once_per_device_of_the_recipient_with_the_ids_as_strings(self):
        """NOTIF-21, NOTIF-72"""
        first = self.register(self.recipient, TOKEN_1)
        second = self.register(self.recipient, TOKEN_2)
        self.register(self.author, 'other-token')

        with self.captureOnCommitCallbacks(execute=True):
            alert = notify(self.message(), actor=self.author)

        data = {'alert_id': str(alert.pk), 'kind': 'reservation-created'}
        self.assertEqual(
            sorted(self.fake.published, key=lambda push: push['arn']),
            sorted([
                {'arn': first.endpoint_arn, 'title': 'Nova reserva', 'body': 'Ana reservou Corte para 20/10 às 09:00.', 'data': data},
                {'arn': second.endpoint_arn, 'title': 'Nova reserva', 'body': 'Ana reservou Corte para 20/10 às 09:00.', 'data': data},
            ], key=lambda push: push['arn']),
        )

    def test_it_does_not_call_sns_to_publish_when_the_recipient_has_no_device(self):
        """NOTIF-22"""
        self.register(self.author, 'other-token')

        with self.captureOnCommitCallbacks(execute=True):
            notify(self.message(), actor=self.author)

        self.assertEqual(Alert.objects.count(), 1)
        self.assertEqual([name for name, _ in self.fake.calls if name == 'publish'], [])

    def test_nothing_is_published_before_the_commit(self):
        """NOTIF-20"""
        self.register(self.recipient, TOKEN_1)

        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            notify(self.message(), actor=self.author)

        self.assertEqual(len(callbacks), 1)
        self.assertEqual(self.fake.published, [])

    def test_a_rolled_back_action_leaves_no_alert_and_no_push(self):
        """NOTIF-20"""
        self.register(self.recipient, TOKEN_1)

        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            with self.assertRaises(Boom), transaction.atomic():
                notify(self.message(), actor=self.author)
                raise Boom

        self.assertEqual(Alert.objects.count(), 0)
        self.assertEqual(callbacks, [])
        self.assertEqual(self.fake.published, [])

    def test_the_author_is_never_notified(self):
        """NOTIF-26"""
        self.register(self.author, TOKEN_1)

        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            result = notify(self.message(recipient=self.author), actor=self.author)

        self.assertIsNone(result)
        self.assertEqual(Alert.objects.count(), 0)
        self.assertEqual((callbacks, self.fake.published), ([], []))


class PublishFailureTest(DispatchTestCase):
    def test_a_failure_on_the_first_device_does_not_stop_the_second_and_keeps_the_alert(self):
        """NOTIF-23"""
        self.register(self.recipient, TOKEN_1)
        self.register(self.recipient, TOKEN_2)
        self.fake.fail_next('publish', 'InternalError')

        with self.assertLogs('notifications.sns', 'WARNING') as logs:
            with self.captureOnCommitCallbacks(execute=True):
                notify(self.message(), actor=self.author)

        self.assertEqual(Alert.objects.count(), 1)
        self.assertEqual(len(self.fake.published), 1)
        self.assertEqual(logs.output, ['WARNING:notifications.sns:sns publish failed: InternalError'])

    def test_an_unexpected_error_never_leaves_the_commit_block(self):
        """NOTIF-23: the view would answer 500 for an action that was already committed."""
        self.register(self.recipient, TOKEN_1)

        with patch.object(type(self.sns), 'publish', side_effect=Boom('unexpected')):
            with self.assertLogs('notifications.dispatch', 'WARNING') as logs:
                with self.captureOnCommitCallbacks(execute=True):
                    notify(self.message(), actor=self.author)

        self.assertEqual(Alert.objects.count(), 1)
        self.assertEqual(logs.output, ['WARNING:notifications.dispatch:push to a device failed: Boom'])

    def test_a_failure_to_read_the_alert_is_logged_and_not_raised(self):
        """NOTIF-23"""
        with patch('notifications.dispatch.Alert.objects') as manager, self.assertLogs('notifications.dispatch', 'WARNING') as logs:
            manager.filter.side_effect = Boom('database down')
            publish_alert(1)

        self.assertEqual(logs.output, ['WARNING:notifications.dispatch:push of alert 1 failed: Boom'])

    def test_the_log_has_neither_the_token_nor_the_arn(self):
        """NOTIF-77"""
        device = self.register(self.recipient, TOKEN_1)
        self.fake.fail_next('publish', 'InternalError')

        with self.assertLogs(level='WARNING') as logs:
            with self.captureOnCommitCallbacks(execute=True):
                notify(self.message(), actor=self.author)

        text = '\n'.join(logs.output)
        self.assertIn('InternalError', text)
        self.assertNotIn(TOKEN_1, text)
        self.assertNotIn(device.endpoint_arn, text)


class EndpointGoneTest(DispatchTestCase):
    def test_a_disabled_endpoint_loses_its_row_and_its_endpoint_and_the_other_device_still_receives(self):
        """NOTIF-24"""
        dead = self.register(self.recipient, TOKEN_1)
        alive = self.register(self.recipient, TOKEN_2)
        self.fake.disable(dead.endpoint_arn)

        with self.assertLogs('notifications.sns', 'WARNING'):
            with self.captureOnCommitCallbacks(execute=True):
                notify(self.message(), actor=self.author)

        self.assertEqual(list(PushDevice.objects.values_list('pk', flat=True)), [alive.pk])
        self.assertEqual(self.fake.deleted, [dead.endpoint_arn])
        self.assertEqual([push['arn'] for push in self.fake.published], [alive.endpoint_arn])

    def test_a_deleted_endpoint_that_sns_no_longer_knows_loses_its_row(self):
        """NOTIF-24"""
        gone = self.register(self.recipient, TOKEN_1)
        del self.fake.endpoints[gone.endpoint_arn]

        with self.assertLogs('notifications.sns', 'WARNING'):
            with self.captureOnCommitCallbacks(execute=True):
                notify(self.message(), actor=self.author)

        self.assertEqual(PushDevice.objects.count(), 0)


class OwnerAtSendTimeTest(DispatchTestCase):
    def test_a_device_that_moved_to_another_account_before_the_send_does_not_get_the_push(self):
        """NOTIF-73"""
        device = self.register(self.recipient, TOKEN_1)

        with self.captureOnCommitCallbacks(execute=True):
            notify(self.message(), actor=self.author)
            PushDevice.objects.filter(pk=device.pk).update(user=self.author)

        self.assertEqual(self.fake.published, [])

    def test_a_device_that_arrived_before_the_send_gets_the_push(self):
        """NOTIF-73"""
        device = self.register(self.author, TOKEN_1)

        with self.captureOnCommitCallbacks(execute=True):
            notify(self.message(), actor=self.author)
            PushDevice.objects.filter(pk=device.pk).update(user=self.recipient)

        self.assertEqual([push['arn'] for push in self.fake.published], [device.endpoint_arn])


class DeleteEndpointsTest(DispatchTestCase):
    def test_it_deletes_every_endpoint(self):
        """NOTIF-11"""
        arns = [self.sns.create_endpoint(TOKEN_1), self.sns.create_endpoint(TOKEN_2)]

        delete_endpoints(arns)

        self.assertEqual(self.fake.deleted, arns)

    def test_a_failure_is_logged_and_the_next_endpoint_is_still_deleted(self):
        """NOTIF-10"""
        arns = [self.sns.create_endpoint(TOKEN_1), self.sns.create_endpoint(TOKEN_2)]
        self.fake.fail_next('delete_endpoint', 'InternalError')

        with self.assertLogs('notifications', 'WARNING'):
            delete_endpoints(arns)

        self.assertEqual(self.fake.deleted, [arns[1]])
