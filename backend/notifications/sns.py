import json
import logging

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings

logger = logging.getLogger(__name__)

PLATFORM_APPLICATION_NAME = 'hairmatch-dev-fcm'
# The Android channel the app creates; a push for another channel would use the silent default.
CHANNEL_ID = 'default'


class SnsError(Exception):
    def __init__(self, code=''):
        super().__init__(code)
        self.code = code


class EndpointGone(SnsError):
    """SNS disabled the endpoint (the FCM token is no longer valid) or no longer knows it."""


class PushUnavailable(SnsError):
    """Anything else that stops a call: SNS down, slow, misconfigured or refusing the request."""


_GONE_CODES = {'EndpointDisabled', 'NotFound'}
# LocalStack answers a publish to a deleted endpoint with InvalidParameter and this text, where SNS answers NotFound.
# Any other InvalidParameter (a malformed message, say) is our bug, and must not delete the phone of a user.
_NO_ENDPOINT_MESSAGE = 'No endpoint found for the target arn'


class SnsService:
    """
    Every call to SNS goes through here. boto3 errors become domain errors
    and each failure is logged with the operation and the error code only:
    neither the FCM token nor the endpoint ARN ever reaches the log.
    """

    def __init__(self, client=None):
        self._client = client
        self._resolved_platform_application_arn = None

    @property
    def client(self):
        if self._client is None:
            # The send runs in the request thread, so these limits cap the worst case at a few seconds per device.
            self._client = boto3.client(
                'sns',
                config=Config(connect_timeout=2, read_timeout=3, retries={'max_attempts': 2, 'mode': 'standard'}),
            )
        return self._client

    @property
    def platform_application_arn(self):
        if settings.SNS_PLATFORM_APPLICATION_ARN:
            return settings.SNS_PLATFORM_APPLICATION_ARN
        if self._resolved_platform_application_arn is None:
            self._resolved_platform_application_arn = self._find_platform_application_arn()
        return self._resolved_platform_application_arn

    def create_endpoint(self, token):
        """Creates the endpoint of the token and returns its ARN. Creating it again for the same token returns the same ARN."""
        arn = self._call(
            'create_platform_endpoint', PlatformApplicationArn=self.platform_application_arn, Token=token,
        )['EndpointArn']
        # SNS may keep an endpoint it disabled after FCM refused the token; this turns it back on.
        self._call('set_endpoint_attributes', EndpointArn=arn, Attributes={'Enabled': 'true', 'Token': token})
        return arn

    def delete_endpoint(self, arn):
        try:
            self._call('delete_endpoint', EndpointArn=arn)
        except EndpointGone:
            pass

    def publish(self, arn, title, body, data):
        """`data` values must be strings: FCM answers INVALID_ARGUMENT otherwise."""
        fcm_message = {
            'message': {
                'notification': {'title': title, 'body': body},
                'data': data,
                'android': {'priority': 'high', 'notification': {'channel_id': CHANNEL_ID}},
            },
        }
        message = {'default': body, 'GCM': json.dumps({'fcmV1Message': fcm_message})}
        self._call('publish', TargetArn=arn, Message=json.dumps(message), MessageStructure='json')

    def _find_platform_application_arn(self):
        token = None
        while True:
            kwargs = {'NextToken': token} if token else {}
            response = self._call('list_platform_applications', **kwargs)
            for application in response['PlatformApplications']:
                if application['PlatformApplicationArn'].endswith(f'/GCM/{PLATFORM_APPLICATION_NAME}'):
                    return application['PlatformApplicationArn']
            token = response.get('NextToken')
            if not token:
                self._log('list_platform_applications', f'{PLATFORM_APPLICATION_NAME} not found')
                raise PushUnavailable(f'{PLATFORM_APPLICATION_NAME} not found')

    def _call(self, operation, **kwargs):
        try:
            return getattr(self.client, operation)(**kwargs)
        except ClientError as exc:
            error = exc.response.get('Error', {})
            code = error.get('Code', '')
            self._log(operation, code)
            gone = code in _GONE_CODES or (code == 'InvalidParameter' and _NO_ENDPOINT_MESSAGE in error.get('Message', ''))
            raise (EndpointGone if gone else PushUnavailable)(code) from exc
        except BotoCoreError as exc:
            code = type(exc).__name__
            self._log(operation, code)
            raise PushUnavailable(code) from exc

    @staticmethod
    def _log(operation, code):
        logger.warning('sns %s failed: %s', operation, code)


_service = None


def get_sns():
    global _service
    if _service is None:
        client = None
        if settings.SNS_USE_FAKE:
            from .sns_fake import FakeSns

            client = FakeSns()
        _service = SnsService(client)
    return _service


def reset_sns():
    global _service
    _service = None
