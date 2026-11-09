import boto3
from botocore.stub import Stubber
from django.core.files.base import ContentFile
from django.test import SimpleTestCase, override_settings
from opentelemetry import trace
from opentelemetry.trace import SpanKind

from hairmatch import testing_telemetry
from hairmatch.storage import S3MediaStorage


def stubbed_storage():
    """A storage on a real boto3 client with stubbed answers. `storage.sent` collects the parameters of each PutObject."""
    client = boto3.client(
        's3', region_name='us-east-2', aws_access_key_id='x', aws_secret_access_key='y', endpoint_url='http://localhost:4566',
    )
    stubber = Stubber(client)
    storage = S3MediaStorage()
    storage._client = client
    storage.sent = []
    client.meta.events.register('provide-client-params.s3.PutObject', lambda params, **kwargs: storage.sent.append(dict(params)))
    return storage, stubber


@override_settings(S3_BUCKET_NAME='media-bucket')
class S3SpanTests(testing_telemetry.TelemetryMixin, SimpleTestCase):
    """TEL-18, TEL-23: the S3 call is a CLIENT span in the trace of the request."""

    def test_put_object_is_a_client_span_child_of_the_request_span(self):
        storage, stubber = stubbed_storage()
        stubber.add_response('put_object', {}, None)
        with stubber:
            with trace.get_tracer('t').start_as_current_span('request') as request:
                storage._save('gallery/1/a.webp', ContentFile(b'webp-bytes'))
        put = self.span('S3.PutObject')
        self.assertEqual(put.kind, SpanKind.CLIENT)
        self.assertEqual(put.context.trace_id, request.get_span_context().trace_id)
        self.assertEqual(put.parent.span_id, request.get_span_context().span_id)
        self.assertEqual((put.attributes['rpc.service'], put.attributes['rpc.method']), ('S3', 'PutObject'))

    def test_delete_object_is_a_child_span_too(self):
        storage, stubber = stubbed_storage()
        stubber.add_response('delete_object', {}, {'Bucket': 'media-bucket', 'Key': 'gallery/1/a.webp'})
        with stubber:
            with trace.get_tracer('t').start_as_current_span('request') as request:
                storage.delete('gallery/1/a.webp')
        delete = self.span('S3.DeleteObject')
        self.assertEqual(delete.parent.span_id, request.get_span_context().span_id)

    def test_the_upload_still_sends_the_content_type_and_the_body(self):
        storage, stubber = stubbed_storage()
        stubber.add_response('put_object', {}, None)
        with stubber:
            name = storage._save('a.png', ContentFile(b'png-bytes'))
        self.assertEqual(name, 'a.png')
        stubber.assert_no_pending_responses()
        (sent,) = storage.sent
        self.assertEqual((sent['Bucket'], sent['Key'], sent['ContentType']), ('media-bucket', 'a.png', 'image/png'))
        self.assertEqual(sent['Body'].read(), b'png-bytes')

    def test_span_has_no_object_key_in_its_attributes(self):
        storage, stubber = stubbed_storage()
        stubber.add_response('put_object', {}, None)
        with stubber:
            storage._save('hairdresser/gallery/77/secret-name.webp', ContentFile(b'x'))
        put = self.span('S3.PutObject')
        self.assertNotIn('secret-name', repr(dict(put.attributes)) + put.name)
