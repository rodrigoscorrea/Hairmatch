from unittest.mock import PropertyMock, patch

from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from opentelemetry.trace import SpanKind
from rest_framework import status

from hairmatch import testing_telemetry
from hairmatch.image_fixtures import make_image_bytes, make_upload
from hairmatch.images import to_webp
from users.tests import GalleryApiTestCase

S3_STORAGES = {
    'default': {'BACKEND': 'hairmatch.storage.S3MediaStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}


class ToWebpSpanTests(testing_telemetry.TelemetryMixin, SimpleTestCase):
    """TEL-24: the conversion span says how big the image was and nothing about what it shows."""

    def test_the_span_carries_only_the_two_byte_counts(self):
        upload = make_upload('praia.png', size=(300, 200), fmt='PNG')
        original = upload.size

        converted = to_webp(upload)

        span = self.span('image.to_webp')
        self.assertEqual(dict(span.attributes), {'image.bytes_in': original, 'image.bytes_out': converted.size})
        self.assertNotIn('praia', repr(span.attributes) + span.name)

    def test_an_invalid_image_marks_the_span_as_failed_without_the_exception_text(self):
        from hairmatch.images import InvalidImage
        from django.core.files.base import ContentFile

        with self.assertRaises(InvalidImage):
            to_webp(ContentFile(b'not an image'))

        span = self.span('image.to_webp')
        self.assertEqual(span.attributes['image.bytes_in'], len(b'not an image'))
        self.assertNotIn('image.bytes_out', span.attributes)
        self.assertEqual(span.status.status_code.name, 'ERROR')
        self.assertEqual(span.attributes['error.type'], 'InvalidImage')


@override_settings(STORAGES=S3_STORAGES, S3_BUCKET_NAME='media-bucket')
class GalleryUploadTraceTests(testing_telemetry.TelemetryMixin, GalleryApiTestCase):
    """TEL-23, TEL-24: converting and storing a gallery photo happen inside the trace of the request."""

    def test_conversion_and_s3_put_are_children_of_the_request_span(self):
        client, stubber = testing_telemetry.stubbed_client('s3')
        stubber.add_client_error('head_object', service_error_code='404', http_status_code=404)
        stubber.add_response('put_object', {})
        testing_telemetry.clear()

        with patch('hairmatch.storage.S3MediaStorage.client', new_callable=PropertyMock, return_value=client), stubber:
            response = self._post(make_upload('praia.png', size=(800, 600), fmt='PNG'))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        request_span = next(s for s in self.spans() if s.kind == SpanKind.SERVER and s.name.startswith('POST'))
        conversion = self.span('image.to_webp')
        put = self.span('S3.PutObject')
        self.assertEqual(conversion.context.trace_id, request_span.context.trace_id)
        self.assertEqual(put.context.trace_id, request_span.context.trace_id)
        self.assertEqual(conversion.parent.span_id, request_span.context.span_id)
        self.assertEqual(put.parent.span_id, request_span.context.span_id)
        self.assertEqual(set(conversion.attributes), {'image.bytes_in', 'image.bytes_out'})
