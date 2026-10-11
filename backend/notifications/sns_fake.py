"""
In-memory stand-in for ``boto3.client('sns')``, used by the test suite.

It raises the same ``botocore.exceptions.ClientError`` codes as SNS, so the real
error mapping runs in tests. ``created``, ``published`` and ``deleted`` record what
the code under test did; ``fail_next`` and ``disable`` make SNS misbehave.
"""
import json
import uuid
from collections import defaultdict, deque

from botocore.exceptions import ClientError

ACCOUNT = '000000000000'
REGION = 'us-east-2'
PLATFORM_APPLICATION_ARN = f'arn:aws:sns:{REGION}:{ACCOUNT}:app/GCM/hairmatch-dev-fcm'


def _client_error(code, operation, message=''):
    return ClientError({'Error': {'Code': code, 'Message': message or code}}, operation)


class FakeSns:
    def __init__(self):
        self.endpoints = {}  # arn -> {'Token', 'Enabled'}
        self.created = []  # arns, one per create_platform_endpoint call
        self.published = []  # {'arn', 'title', 'body', 'data'}, one per publish
        self.deleted = []  # arns, one per delete_endpoint call
        self.calls = []
        self._failures = defaultdict(deque)

    # -- test helpers -------------------------------------------------------

    def fail_next(self, operation, error):
        """Make the next ``operation`` call raise ``error`` (an exception or an SNS error code)."""
        self._failures[operation].append(error)

    def disable(self, arn):
        """Make SNS refuse every publish to the endpoint, as it does after FCM drops the token."""
        self.endpoints[arn]['Enabled'] = 'false'

    def _begin(self, operation, **kwargs):
        self.calls.append((operation, kwargs))
        queue = self._failures[operation]
        if queue:
            error = queue.popleft()
            if isinstance(error, str):
                raise _client_error(error, operation)
            raise error

    # -- the part of the SNS API the service uses ---------------------------

    def list_platform_applications(self, **kwargs):
        self._begin('list_platform_applications', **kwargs)
        return {'PlatformApplications': [{'PlatformApplicationArn': PLATFORM_APPLICATION_ARN, 'Attributes': {}}]}

    def create_platform_endpoint(self, PlatformApplicationArn, Token, **kwargs):
        self._begin('create_platform_endpoint', PlatformApplicationArn=PlatformApplicationArn, Token=Token, **kwargs)
        # SNS answers the same ARN to the same token.
        for arn, endpoint in self.endpoints.items():
            if endpoint['Token'] == Token:
                self.created.append(arn)
                return {'EndpointArn': arn}
        arn = f'arn:aws:sns:{REGION}:{ACCOUNT}:endpoint/GCM/hairmatch-dev-fcm/{uuid.uuid4()}'
        self.endpoints[arn] = {'Token': Token, 'Enabled': 'true'}
        self.created.append(arn)
        return {'EndpointArn': arn}

    def set_endpoint_attributes(self, EndpointArn, Attributes):
        self._begin('set_endpoint_attributes', EndpointArn=EndpointArn, Attributes=Attributes)
        if EndpointArn not in self.endpoints:
            raise _client_error('NotFound', 'set_endpoint_attributes')
        self.endpoints[EndpointArn].update(Attributes)
        return {}

    def publish(self, TargetArn, Message, MessageStructure):
        self._begin('publish', TargetArn=TargetArn, Message=Message, MessageStructure=MessageStructure)
        if TargetArn not in self.endpoints:
            raise _client_error('NotFound', 'publish')
        if self.endpoints[TargetArn]['Enabled'] != 'true':
            raise _client_error('EndpointDisabled', 'publish')
        assert MessageStructure == 'json'
        fcm_message = json.loads(json.loads(Message)['GCM'])['fcmV1Message']['message']
        data = fcm_message['data']
        if not all(isinstance(value, str) for value in data.values()):
            raise _client_error('InvalidParameter', 'publish', 'FCM data values must be strings')
        notification = fcm_message['notification']
        self.published.append(
            {'arn': TargetArn, 'title': notification['title'], 'body': notification['body'], 'data': data}
        )
        return {'MessageId': str(uuid.uuid4())}

    def delete_endpoint(self, EndpointArn):
        self._begin('delete_endpoint', EndpointArn=EndpointArn)
        self.deleted.append(EndpointArn)
        self.endpoints.pop(EndpointArn, None)
        return {}
