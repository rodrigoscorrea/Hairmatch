import json

import boto3
from botocore.exceptions import EndpointConnectionError, ReadTimeoutError
from botocore.stub import Stubber
from django.test import SimpleTestCase, override_settings

from notifications.sns import EndpointGone, PushUnavailable, SnsService, get_sns, reset_sns
from notifications.sns_fake import FakeSns

APP_ARN = 'arn:aws:sns:us-east-2:123456789012:app/GCM/hairmatch-prod-fcm'
ENDPOINT_ARN = 'arn:aws:sns:us-east-2:123456789012:endpoint/GCM/hairmatch-prod-fcm/abc-123'
TOKEN = 'fcm-token-very-secret'


def real_client():
    return boto3.client(
        'sns', region_name='us-east-2', aws_access_key_id='test', aws_secret_access_key='test',
    )


class Captured:
    """Matches any value and keeps it, so a test can read the parameter the code sent."""

    value = None

    def __eq__(self, other):
        self.value = other
        return True


class StubbedSnsTest(SimpleTestCase):
    def setUp(self):
        self.client = real_client()
        self.stubber = Stubber(self.client)
        self.stubber.activate()
        self.addCleanup(self.stubber.deactivate)
        self.service = SnsService(self.client)


@override_settings(SNS_PLATFORM_APPLICATION_ARN=APP_ARN)
class CreateEndpointTest(StubbedSnsTest):
    def test_it_creates_the_endpoint_without_custom_data_and_then_enables_it_with_the_token(self):
        self.stubber.add_response(
            'create_platform_endpoint', {'EndpointArn': ENDPOINT_ARN},
            {'PlatformApplicationArn': APP_ARN, 'Token': TOKEN},
        )
        self.stubber.add_response(
            'set_endpoint_attributes', {},
            {'EndpointArn': ENDPOINT_ARN, 'Attributes': {'Enabled': 'true', 'Token': TOKEN}},
        )

        arn = self.service.create_endpoint(TOKEN)

        self.assertEqual(arn, ENDPOINT_ARN)
        self.stubber.assert_no_pending_responses()

    def test_a_failure_to_create_the_endpoint_is_push_unavailable(self):
        """NOTIF-06"""
        self.stubber.add_client_error('create_platform_endpoint', service_error_code='InternalError')

        with self.assertRaises(PushUnavailable) as raised:
            self.service.create_endpoint(TOKEN)

        self.assertEqual(raised.exception.code, 'InternalError')

    def test_a_failure_to_enable_the_endpoint_is_push_unavailable(self):
        """NOTIF-06"""
        self.stubber.add_response('create_platform_endpoint', {'EndpointArn': ENDPOINT_ARN})
        self.stubber.add_client_error('set_endpoint_attributes', service_error_code='InvalidParameter')

        with self.assertRaises(PushUnavailable):
            self.service.create_endpoint(TOKEN)

    def test_the_failure_log_has_the_operation_and_the_code_but_not_the_token(self):
        """NOTIF-77, NOTIF-06"""
        self.stubber.add_client_error(
            'create_platform_endpoint', service_error_code='InternalError', service_message=f'bad token {TOKEN}',
        )

        with self.assertLogs('notifications.sns', 'WARNING') as logs, self.assertRaises(PushUnavailable):
            self.service.create_endpoint(TOKEN)

        self.assertEqual(logs.output, ['WARNING:notifications.sns:sns create_platform_endpoint failed: InternalError'])


@override_settings(SNS_PLATFORM_APPLICATION_ARN=APP_ARN)
class PublishTest(StubbedSnsTest):
    def test_it_sends_the_fcm_v1_message_with_string_data_and_the_default_channel(self):
        """NOTIF-21"""
        message = Captured()
        self.stubber.add_response(
            'publish', {'MessageId': 'm-1'},
            {'TargetArn': ENDPOINT_ARN, 'Message': message, 'MessageStructure': 'json'},
        )

        self.service.publish(ENDPOINT_ARN, 'Nova reserva', 'Ana reservou Corte.', {'alert_id': '7', 'kind': 'reservation-created'})

        sent = json.loads(message.value)
        self.assertEqual(sent['default'], 'Ana reservou Corte.')
        self.assertEqual(json.loads(sent['GCM']), {
            'fcmV1Message': {'message': {
                'notification': {'title': 'Nova reserva', 'body': 'Ana reservou Corte.'},
                'data': {'alert_id': '7', 'kind': 'reservation-created'},
                'android': {'priority': 'high', 'notification': {'channel_id': 'default'}},
            }},
        })

    def test_a_disabled_endpoint_is_endpoint_gone(self):
        """NOTIF-24"""
        self.stubber.add_client_error('publish', service_error_code='EndpointDisabled')

        with self.assertRaises(EndpointGone) as raised:
            self.service.publish(ENDPOINT_ARN, 't', 'b', {})

        self.assertEqual(raised.exception.code, 'EndpointDisabled')

    def test_an_unknown_endpoint_is_endpoint_gone(self):
        """NOTIF-24"""
        self.stubber.add_client_error('publish', service_error_code='NotFound')

        with self.assertRaises(EndpointGone):
            self.service.publish(ENDPOINT_ARN, 't', 'b', {})

    def test_any_other_client_error_is_push_unavailable(self):
        """NOTIF-23"""
        self.stubber.add_client_error('publish', service_error_code='InternalError')

        with self.assertRaises(PushUnavailable) as raised:
            self.service.publish(ENDPOINT_ARN, 't', 'b', {})

        self.assertNotIsInstance(raised.exception, EndpointGone)

    def test_the_failure_log_has_the_operation_and_the_code_but_not_the_arn(self):
        """NOTIF-77, NOTIF-23"""
        self.stubber.add_client_error(
            'publish', service_error_code='InternalError', service_message=f'failed for {ENDPOINT_ARN}',
        )

        with self.assertLogs('notifications.sns', 'WARNING') as logs, self.assertRaises(PushUnavailable):
            self.service.publish(ENDPOINT_ARN, 't', 'b', {})

        self.assertEqual(logs.output, ['WARNING:notifications.sns:sns publish failed: InternalError'])


class BrokenClient:
    def __init__(self, error):
        self.error = error

    def publish(self, **kwargs):
        raise self.error


class UnreachableSnsTest(SimpleTestCase):
    def test_a_connection_error_is_push_unavailable(self):
        """NOTIF-23"""
        service = SnsService(BrokenClient(EndpointConnectionError(endpoint_url='http://sns')))

        with self.assertLogs('notifications.sns', 'WARNING'), self.assertRaises(PushUnavailable) as raised:
            service.publish(ENDPOINT_ARN, 't', 'b', {})

        self.assertEqual(raised.exception.code, 'EndpointConnectionError')

    def test_a_read_timeout_is_push_unavailable(self):
        """NOTIF-23"""
        service = SnsService(BrokenClient(ReadTimeoutError(endpoint_url='http://sns')))

        with self.assertLogs('notifications.sns', 'WARNING'), self.assertRaises(PushUnavailable) as raised:
            service.publish(ENDPOINT_ARN, 't', 'b', {})

        self.assertEqual(raised.exception.code, 'ReadTimeoutError')


class DeleteEndpointTest(StubbedSnsTest):
    def test_it_deletes_the_endpoint(self):
        """NOTIF-07"""
        self.stubber.add_response('delete_endpoint', {}, {'EndpointArn': ENDPOINT_ARN})

        self.service.delete_endpoint(ENDPOINT_ARN)

        self.stubber.assert_no_pending_responses()

    def test_an_unknown_endpoint_is_not_an_error(self):
        self.stubber.add_client_error('delete_endpoint', service_error_code='NotFound')

        self.service.delete_endpoint(ENDPOINT_ARN)

    def test_any_other_failure_is_push_unavailable(self):
        """NOTIF-10"""
        self.stubber.add_client_error('delete_endpoint', service_error_code='InternalError')

        with self.assertRaises(PushUnavailable):
            self.service.delete_endpoint(ENDPOINT_ARN)


def application(name, region='us-east-2'):
    return {'PlatformApplicationArn': f'arn:aws:sns:{region}:123456789012:app/GCM/{name}', 'Attributes': {}}


class PlatformApplicationArnTest(StubbedSnsTest):
    @override_settings(SNS_PLATFORM_APPLICATION_ARN='')
    def test_with_the_setting_empty_it_finds_hairmatch_dev_fcm_on_the_second_page(self):
        """NOTIF-69"""
        self.stubber.add_response('list_platform_applications', {
            'PlatformApplications': [application('other-app')], 'NextToken': 'page-2',
        }, {})
        self.stubber.add_response('list_platform_applications', {
            'PlatformApplications': [application('hairmatch-dev-fcm')],
        }, {'NextToken': 'page-2'})

        arn = self.service.platform_application_arn

        self.assertEqual(arn, 'arn:aws:sns:us-east-2:123456789012:app/GCM/hairmatch-dev-fcm')
        self.stubber.assert_no_pending_responses()

    @override_settings(SNS_PLATFORM_APPLICATION_ARN='')
    def test_the_lookup_is_done_once(self):
        self.stubber.add_response('list_platform_applications', {'PlatformApplications': [application('hairmatch-dev-fcm')]})

        first = self.service.platform_application_arn
        second = self.service.platform_application_arn

        self.assertEqual(first, second)
        self.stubber.assert_no_pending_responses()

    @override_settings(SNS_PLATFORM_APPLICATION_ARN=APP_ARN)
    def test_with_the_setting_filled_it_uses_the_setting_without_calling_sns(self):
        """NOTIF-69: the stubber has no response queued, so any call would fail."""
        self.assertEqual(self.service.platform_application_arn, APP_ARN)

    @override_settings(SNS_PLATFORM_APPLICATION_ARN='')
    def test_without_the_application_it_is_push_unavailable(self):
        self.stubber.add_response('list_platform_applications', {'PlatformApplications': [application('other-app')]})

        with self.assertLogs('notifications.sns', 'WARNING'), self.assertRaises(PushUnavailable):
            self.service.platform_application_arn


class FakeSnsTest(SimpleTestCase):
    def setUp(self):
        reset_sns()
        self.addCleanup(reset_sns)

    def test_the_suite_uses_the_fake(self):
        """NOTIF-70"""
        self.assertIsInstance(get_sns().client, FakeSns)

    def test_reset_gives_a_clean_fake(self):
        get_sns().create_endpoint(TOKEN)

        reset_sns()

        self.assertEqual(get_sns().client.created, [])

    def test_it_records_creations_publications_and_removals(self):
        sns = get_sns()

        arn = sns.create_endpoint(TOKEN)
        sns.publish(arn, 'Nova reserva', 'Corpo.', {'alert_id': '1', 'kind': 'reservation-created'})
        sns.delete_endpoint(arn)

        fake = sns.client
        self.assertEqual(fake.created, [arn])
        self.assertEqual(fake.published, [
            {'arn': arn, 'title': 'Nova reserva', 'body': 'Corpo.', 'data': {'alert_id': '1', 'kind': 'reservation-created'}},
        ])
        self.assertEqual(fake.deleted, [arn])

    def test_the_same_token_gets_the_same_endpoint(self):
        sns = get_sns()

        self.assertEqual(sns.create_endpoint(TOKEN), sns.create_endpoint(TOKEN))

    def test_fail_next_fails_only_the_next_call_of_that_operation(self):
        sns = get_sns()
        arn = sns.create_endpoint(TOKEN)
        sns.client.fail_next('publish', 'InternalError')

        with self.assertLogs('notifications.sns', 'WARNING'), self.assertRaises(PushUnavailable):
            sns.publish(arn, 't', 'b', {})
        sns.publish(arn, 't', 'b', {})

        self.assertEqual(len(sns.client.published), 1)

    def test_disable_makes_the_endpoint_gone_until_it_is_created_again(self):
        sns = get_sns()
        arn = sns.create_endpoint(TOKEN)
        sns.client.disable(arn)

        with self.assertLogs('notifications.sns', 'WARNING'), self.assertRaises(EndpointGone):
            sns.publish(arn, 't', 'b', {})
        sns.create_endpoint(TOKEN)
        sns.publish(arn, 't', 'b', {})

        self.assertEqual(len(sns.client.published), 1)

    def test_the_fake_refuses_data_that_is_not_made_of_strings_like_fcm(self):
        sns = get_sns()
        arn = sns.create_endpoint(TOKEN)

        with self.assertLogs('notifications.sns', 'WARNING'), self.assertRaises(PushUnavailable):
            sns.publish(arn, 't', 'b', {'alert_id': 1})
