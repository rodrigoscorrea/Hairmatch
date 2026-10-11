import threading
from unittest.mock import patch

from django.db import connection
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIClient

from hairmatch.problem_testing import assert_problem
from notifications.models import PushDevice
from notifications.sns import SnsService, get_sns

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
