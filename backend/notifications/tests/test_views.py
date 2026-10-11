import datetime
import threading
from unittest.mock import patch

from botocore.exceptions import EndpointConnectionError
from django.db import connection
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from hairmatch.problem_testing import assert_problem
from notifications.models import Alert, PushDevice
from notifications.sns import SnsService, get_sns
from users.cognito import get_cognito
from users.models import User

from .helpers import login, make_user

URL = '/api/users/me/push-devices'
TOKEN = 'fcm-token-of-the-phone'


def post(client, token=TOKEN):
    return client.post(URL, data={'token': token}, format='json')


class PushDeviceTestCase(TestCase):
    def setUp(self):
        self.user = make_user('user@example.com', '5592900000001')
        self.other = make_user('other@example.com', '5592900000002', 'hairdresser')
        self.client_user = login(self.user)
        self.client_other = login(self.other)
        self.fake = get_sns().client

    def rows(self):
        return list(PushDevice.objects.order_by('id').values_list('id', 'user_id', 'token', 'endpoint_arn'))


class RegisterDeviceTest(PushDeviceTestCase):
    def test_a_new_token_creates_the_endpoint_and_the_row_and_answers_201_with_the_id(self):
        """NOTIF-01"""
        response = post(self.client_user)

        device = PushDevice.objects.get()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), {'data': {'id': device.id}})
        self.assertEqual((device.user_id, device.token), (self.user.id, TOKEN))
        self.assertEqual(self.fake.created, [device.endpoint_arn])
        self.assertEqual(self.fake.endpoints[device.endpoint_arn], {'Token': TOKEN, 'Enabled': 'true'})

    def test_a_token_that_is_already_the_accounts_answers_200_with_the_same_id_and_keeps_one_row(self):
        """NOTIF-02"""
        first = post(self.client_user).json()['data']['id']
        before = self.rows()

        response = post(self.client_user)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'data': {'id': first}})
        self.assertEqual(self.rows(), before)
        self.assertEqual(len(self.fake.created), 1)

    def test_a_token_of_another_account_moves_to_the_session_account(self):
        """NOTIF-03"""
        first = post(self.client_other).json()['data']['id']

        response = post(self.client_user)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), {'data': {'id': first}})
        self.assertEqual([(user_id, token) for _, user_id, token, _ in self.rows()], [(self.user.id, TOKEN)])
        self.assertEqual(PushDevice.objects.filter(user=self.other).count(), 0)

    def test_a_post_that_loses_the_race_for_a_new_token_answers_with_the_row_that_won(self):
        """NOTIF-04: a simultaneous POST stores the token while this one is still talking to SNS."""
        create_endpoint = SnsService.create_endpoint

        def create_then_lose(service, token):
            arn = create_endpoint(service, token)
            PushDevice.objects.create(user=self.user, token=token, endpoint_arn=arn)
            return arn

        with patch.object(SnsService, 'create_endpoint', create_then_lose):
            response = post(self.client_user)

        device = PushDevice.objects.get()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'data': {'id': device.id}})

    def test_a_token_with_spaces_is_stored_without_them(self):
        """NOTIF-05"""
        response = post(self.client_user, f'  {TOKEN}  ')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(PushDevice.objects.get().token, TOKEN)

    def test_a_token_of_1024_characters_is_accepted(self):
        """NOTIF-05"""
        response = post(self.client_user, 'x' * 1024)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(PushDevice.objects.get().token), 1024)

    def test_an_invalid_token_answers_400_on_the_token_pointer_and_stores_nothing(self):
        """NOTIF-05"""
        invalid = {
            'missing': {}, 'not a string': {'token': 123}, 'null': {'token': None}, 'empty': {'token': ''},
            'only spaces': {'token': '   '}, 'too long': {'token': 'x' * 1025},
        }
        for name, body in invalid.items():
            with self.subTest(name):
                response = self.client_user.post(URL, data=body, format='json')

                body = assert_problem(response, 'validation-error')
                self.assertEqual([error['pointer'] for error in body['errors']], ['#/token'])
        self.assertEqual(PushDevice.objects.count(), 0)
        self.assertEqual(self.fake.created, [])

    def test_a_failing_sns_answers_503_push_unavailable_stores_nothing_and_logs_without_the_token(self):
        """NOTIF-06"""
        self.fake.fail_next('create_platform_endpoint', 'InternalError')

        with self.assertLogs(level='WARNING') as logs:
            response = post(self.client_user)

        assert_problem(response, 'push-unavailable')
        self.assertEqual(PushDevice.objects.count(), 0)
        text = '\n'.join(logs.output)
        self.assertIn('create_platform_endpoint', text)
        self.assertIn('InternalError', text)
        self.assertNotIn(TOKEN, text)

    def test_without_a_session_it_answers_401_and_stores_nothing(self):
        """NOTIF-09"""
        response = post(APIClient())

        assert_problem(response, 'invalid-session')
        self.assertEqual(PushDevice.objects.count(), 0)
        self.assertEqual(self.fake.created, [])


class DeleteDeviceTest(PushDeviceTestCase):
    def setUp(self):
        super().setUp()
        self.device_id = post(self.client_user).json()['data']['id']
        self.arn = PushDevice.objects.get().endpoint_arn

    def url(self, device_id=None):
        return f'{URL}/{device_id or self.device_id}'

    def test_it_deletes_the_row_answers_204_without_a_body_and_deletes_the_endpoint_at_the_commit(self):
        """NOTIF-07"""
        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            response = self.client_user.delete(self.url())

        self.assertEqual((response.status_code, response.content), (204, b''))
        self.assertEqual(PushDevice.objects.count(), 0)
        self.assertEqual(self.fake.deleted, [])
        self.assertEqual(len(callbacks), 1)
        callbacks[0]()
        self.assertEqual(self.fake.deleted, [self.arn])

    def test_a_device_of_another_account_answers_404_and_changes_nothing(self):
        """NOTIF-08"""
        before = self.rows()

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client_other.delete(self.url())

        assert_problem(response, 'not-found')
        self.assertEqual(self.rows(), before)
        self.assertEqual(self.fake.deleted, [])

    def test_an_id_that_does_not_exist_answers_404(self):
        """NOTIF-08"""
        response = self.client_user.delete(self.url(999999))

        assert_problem(response, 'not-found')
        self.assertEqual(PushDevice.objects.count(), 1)

    def test_without_a_session_it_answers_401_and_changes_nothing(self):
        """NOTIF-09"""
        response = APIClient().delete(self.url())

        assert_problem(response, 'invalid-session')
        self.assertEqual(PushDevice.objects.count(), 1)
        self.assertEqual(self.fake.deleted, [])

    def test_a_failure_to_delete_the_endpoint_still_answers_204_and_logs_it(self):
        """NOTIF-10"""
        self.fake.fail_next('delete_endpoint', 'InternalError')

        with self.assertLogs('notifications', 'WARNING') as logs:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client_user.delete(self.url())

        self.assertEqual(response.status_code, 204)
        self.assertEqual(PushDevice.objects.count(), 0)
        self.assertIn('sns delete_endpoint failed: InternalError', '\n'.join(logs.output))


class SimultaneousRegisterTest(TransactionTestCase):
    """NOTIF-04: two requests with the same token store one row."""

    def test_two_simultaneous_posts_of_the_same_token_leave_one_row(self):
        user = make_user('race@example.com', '5592900000010')
        token = login(user).cookies['jwt'].value
        barrier = threading.Barrier(2)
        statuses, failures = [], []

        def register():
            try:
                client = APIClient()
                client.cookies['jwt'] = token
                barrier.wait(timeout=10)
                statuses.append(post(client).status_code)
            except Exception as exc:  # reported below: an exception in a thread does not fail the test
                failures.append(exc)
            finally:
                connection.close()

        threads = [threading.Thread(target=register) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)

        self.assertEqual(failures, [])
        self.assertEqual(PushDevice.objects.filter(token=TOKEN).count(), 1)
        self.assertEqual(sorted(statuses), [200, 201])


class DeleteAccountTest(PushDeviceTestCase):
    """DELETE /api/users/me (RT-10) takes the phones and the alerts of the account with it."""

    ACCOUNT_URL = '/api/users/me'

    def alert(self, recipient):
        return Alert.objects.create(recipient=recipient, kind='reservation-created', title='Nova reserva', body='Corpo.')

    def setUp(self):
        super().setUp()
        post(self.client_user, 'token-a')
        post(self.client_user, 'token-b')
        post(self.client_other, 'token-c')
        for _ in range(3):
            self.alert(self.user)
        self.kept_alert = self.alert(self.other)
        self.arns = list(PushDevice.objects.filter(user=self.user).values_list('endpoint_arn', flat=True))
        self.kept_arn = PushDevice.objects.get(user=self.other).endpoint_arn

    def test_it_removes_the_devices_and_alerts_of_the_account_and_their_endpoints_at_the_commit(self):
        """NOTIF-11, NOTIF-46"""
        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            response = self.client_user.delete(self.ACCOUNT_URL)

        self.assertEqual(response.status_code, 204)
        self.assertEqual(PushDevice.objects.filter(user_id=self.user.id).count(), 0)
        self.assertEqual(Alert.objects.filter(recipient_id=self.user.id).count(), 0)
        self.assertEqual(self.fake.deleted, [])
        for callback in callbacks:
            callback()
        self.assertEqual(sorted(self.fake.deleted), sorted(self.arns))
        self.assertEqual(len(self.fake.deleted), 2)

    def test_the_devices_and_alerts_of_other_accounts_stay(self):
        """NOTIF-11, NOTIF-46"""
        with self.captureOnCommitCallbacks(execute=True):
            self.client_user.delete(self.ACCOUNT_URL)

        self.assertEqual(list(PushDevice.objects.values_list('endpoint_arn', flat=True)), [self.kept_arn])
        self.assertEqual(list(Alert.objects.all()), [self.kept_alert])
        self.assertNotIn(self.kept_arn, self.fake.deleted)

    def test_a_failure_to_delete_an_endpoint_does_not_change_the_answer(self):
        """NOTIF-11, NOTIF-10"""
        self.fake.fail_next('delete_endpoint', 'InternalError')

        with self.assertLogs('notifications', 'WARNING'):
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client_user.delete(self.ACCOUNT_URL)

        self.assertEqual(response.status_code, 204)
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())
        self.assertEqual(len(self.fake.deleted), 1)

    def test_a_deletion_that_cognito_undoes_keeps_the_rows_and_deletes_no_endpoint(self):
        """NOTIF-11"""
        get_cognito().client.fail_next('admin_delete_user', EndpointConnectionError(endpoint_url='http://x'))

        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            response = self.client_user.delete(self.ACCOUNT_URL)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(PushDevice.objects.filter(user_id=self.user.id).count(), 2)
        self.assertEqual(Alert.objects.filter(recipient_id=self.user.id).count(), 3)
        self.assertEqual(callbacks, [])
        self.assertEqual(self.fake.deleted, [])


ALERTS_URL = '/api/users/me/alerts'


def make_alert(recipient, title='Nova reserva', age_minutes=0, read=False):
    now = timezone.now()
    alert = Alert.objects.create(
        recipient=recipient, kind='reservation-created', title=title, body='Ana reservou Corte.', data={'reservation_id': 7},
    )
    # created_at is auto_now_add, so the age is written afterwards.
    Alert.objects.filter(pk=alert.pk).update(
        created_at=now - datetime.timedelta(minutes=age_minutes), read_at=now if read else None,
    )
    return Alert.objects.get(pk=alert.pk)


class AlertTestCase(TestCase):
    def setUp(self):
        self.user = make_user('user@example.com', '5592900000001')
        self.other = make_user('other@example.com', '5592900000002', 'hairdresser')
        self.client_user = login(self.user)
        self.client_other = login(self.other)

    def patch(self, client, url, body):
        return client.patch(url, data=body, format='json')


class ListAlertsTest(AlertTestCase):
    def test_it_answers_200_with_the_alerts_in_the_format_of_the_spec(self):
        """NOTIF-38"""
        alert = make_alert(self.user)

        response = self.client_user.get(ALERTS_URL)

        self.assertEqual(response.status_code, 200)
        body = response.json()['data']
        self.assertEqual(body['unread_count'], 1)
        self.assertEqual(len(body['alerts']), 1)
        self.assertEqual(body['alerts'][0], {
            'id': alert.id, 'kind': 'reservation-created', 'title': 'Nova reserva', 'body': 'Ana reservou Corte.',
            'data': {'reservation_id': 7}, 'read': False,
            'created_at': body['alerts'][0]['created_at'],
        })
        self.assertEqual(datetime.datetime.fromisoformat(body['alerts'][0]['created_at']), alert.created_at)

    def test_a_read_alert_comes_with_read_true(self):
        """NOTIF-38"""
        make_alert(self.user, read=True)

        body = self.client_user.get(ALERTS_URL).json()['data']

        self.assertEqual([alert['read'] for alert in body['alerts']], [True])
        self.assertEqual(body['unread_count'], 0)

    def test_it_returns_the_50_newest_alerts_newest_first_whatever_the_insertion_order(self):
        """NOTIF-38, NOTIF-39"""
        # Inserted oldest-last on purpose: only the ordering can put the newest first.
        alerts = [make_alert(self.user, title=f'Alerta {minutes}', age_minutes=minutes) for minutes in range(55, 0, -1)]
        newest_first = sorted(alerts, key=lambda alert: alert.created_at, reverse=True)

        body = self.client_user.get(ALERTS_URL).json()['data']

        self.assertEqual([alert['id'] for alert in body['alerts']], [alert.id for alert in newest_first[:50]])
        self.assertEqual(len(body['alerts']), 50)

    def test_a_tie_on_created_at_is_broken_by_the_larger_id_first(self):
        """NOTIF-39"""
        first = make_alert(self.user)
        second = make_alert(self.user)
        Alert.objects.update(created_at=timezone.now())

        body = self.client_user.get(ALERTS_URL).json()['data']

        self.assertEqual([alert['id'] for alert in body['alerts']], [second.id, first.id])

    def test_the_unread_count_counts_every_unread_alert_even_those_beyond_the_50(self):
        """NOTIF-38"""
        for minutes in range(1, 56):
            make_alert(self.user, age_minutes=minutes, read=minutes % 11 == 0)
        read_alerts = Alert.objects.filter(recipient=self.user, read_at__isnull=False).count()

        body = self.client_user.get(ALERTS_URL).json()['data']

        self.assertEqual(read_alerts, 5)
        self.assertEqual(body['unread_count'], 50)
        self.assertEqual(len(body['alerts']), 50)

    def test_it_never_returns_the_alerts_of_another_account(self):
        """NOTIF-39"""
        mine = make_alert(self.user)
        make_alert(self.other)
        make_alert(self.other)

        body = self.client_user.get(ALERTS_URL).json()['data']

        self.assertEqual([alert['id'] for alert in body['alerts']], [mine.id])
        self.assertEqual(body['unread_count'], 1)

    def test_without_alerts_it_answers_an_empty_list_and_zero(self):
        """NOTIF-38"""
        response = self.client_user.get(ALERTS_URL)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'data': {'alerts': [], 'unread_count': 0}})


class MarkAlertTest(AlertTestCase):
    def setUp(self):
        super().setUp()
        self.alert = make_alert(self.user)

    def url(self, alert_id=None):
        return f'{ALERTS_URL}/{alert_id or self.alert.id}'

    def test_read_true_stores_the_moment_and_answers_200_with_the_alert(self):
        """NOTIF-40"""
        before = timezone.now()

        response = self.patch(self.client_user, self.url(), {'read': True})

        self.alert.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['id'], self.alert.id)
        self.assertIs(response.json()['data']['read'], True)
        self.assertGreaterEqual(self.alert.read_at, before)

    def test_read_false_clears_the_moment_and_answers_200_with_the_alert(self):
        """NOTIF-40"""
        Alert.objects.filter(pk=self.alert.pk).update(read_at=timezone.now())

        response = self.patch(self.client_user, self.url(), {'read': False})

        self.alert.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertIs(response.json()['data']['read'], False)
        self.assertIsNone(self.alert.read_at)

    def test_an_alert_of_another_account_answers_404_and_stays_unread(self):
        """NOTIF-44"""
        response = self.patch(self.client_other, self.url(), {'read': True})

        assert_problem(response, 'not-found')
        self.alert.refresh_from_db()
        self.assertIsNone(self.alert.read_at)

    def test_an_id_that_does_not_exist_answers_404(self):
        """NOTIF-44"""
        response = self.patch(self.client_user, self.url(999999), {'read': True})

        assert_problem(response, 'not-found')

    def test_a_read_that_is_missing_or_not_a_boolean_answers_400_on_the_read_pointer_and_changes_nothing(self):
        """NOTIF-42"""
        for name, body in {'missing': {}, 'string': {'read': 'true'}, 'number': {'read': 1}, 'null': {'read': None}}.items():
            with self.subTest(name):
                response = self.patch(self.client_user, self.url(), body)

                body = assert_problem(response, 'validation-error')
                self.assertEqual([error['pointer'] for error in body['errors']], ['#/read'])
        self.alert.refresh_from_db()
        self.assertIsNone(self.alert.read_at)

    def test_an_invalid_body_on_a_missing_alert_answers_400_before_the_404(self):
        """NOTIF-42, NOTIF-44: the body is checked first (L-019)."""
        response = self.patch(self.client_user, self.url(999999), {'read': 'yes'})

        assert_problem(response, 'validation-error')

    def test_without_a_session_it_answers_401_and_changes_nothing(self):
        """NOTIF-45"""
        response = self.patch(APIClient(), self.url(), {'read': True})

        assert_problem(response, 'invalid-session')
        self.alert.refresh_from_db()
        self.assertIsNone(self.alert.read_at)


class MarkAllAlertsTest(AlertTestCase):
    def test_read_true_marks_every_alert_of_the_account_and_none_of_another_with_204(self):
        """NOTIF-41"""
        mine = [make_alert(self.user), make_alert(self.user, read=True), make_alert(self.user)]
        theirs = make_alert(self.other)

        response = self.patch(self.client_user, ALERTS_URL, {'read': True})

        self.assertEqual((response.status_code, response.content), (204, b''))
        self.assertEqual(Alert.objects.filter(pk__in=[alert.pk for alert in mine], read_at__isnull=False).count(), 3)
        theirs.refresh_from_db()
        self.assertIsNone(theirs.read_at)

    def test_it_keeps_the_moment_of_an_alert_that_was_already_read(self):
        """NOTIF-41"""
        already = make_alert(self.user, read=True)
        before = already.read_at

        self.patch(self.client_user, ALERTS_URL, {'read': True})

        already.refresh_from_db()
        self.assertEqual(already.read_at, before)

    def test_read_false_answers_400_on_the_read_pointer_and_changes_nothing(self):
        """NOTIF-43"""
        read = make_alert(self.user, read=True)
        unread = make_alert(self.user)

        response = self.patch(self.client_user, ALERTS_URL, {'read': False})

        body = assert_problem(response, 'validation-error')
        self.assertEqual([error['pointer'] for error in body['errors']], ['#/read'])
        read.refresh_from_db()
        unread.refresh_from_db()
        self.assertEqual((read.read_at is not None, unread.read_at is None), (True, True))

    def test_a_read_that_is_missing_or_not_a_boolean_answers_400_on_the_read_pointer(self):
        """NOTIF-42"""
        make_alert(self.user)
        for name, body in {'missing': {}, 'string': {'read': 'true'}, 'number': {'read': 1}}.items():
            with self.subTest(name):
                response = self.patch(self.client_user, ALERTS_URL, body)

                body = assert_problem(response, 'validation-error')
                self.assertEqual([error['pointer'] for error in body['errors']], ['#/read'])
        self.assertEqual(Alert.objects.filter(read_at__isnull=False).count(), 0)


class AlertsWithoutSessionTest(AlertTestCase):
    def test_every_alert_route_answers_401(self):
        """NOTIF-45"""
        anonymous = APIClient()
        calls = {
            'GET collection': lambda: anonymous.get(ALERTS_URL),
            'PATCH collection': lambda: self.patch(anonymous, ALERTS_URL, {'read': True}),
            'PATCH detail': lambda: self.patch(anonymous, f'{ALERTS_URL}/1', {'read': True}),
        }
        for name, call in calls.items():
            with self.subTest(name):
                assert_problem(call(), 'invalid-session')
