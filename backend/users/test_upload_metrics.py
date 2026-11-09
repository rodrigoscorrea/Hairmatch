from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from hairmatch import testing_telemetry
from hairmatch.image_fixtures import make_upload
from users.models import GALLERY_MAX_PHOTOS, GalleryPhoto, User
from users.tests import GalleryApiTestCase

NOT_AN_IMAGE = b'this is not an image' * 10
OVER_5_MB = b'\0' * (5 * 1024 * 1024 + 1)


class UploadCounterTests(testing_telemetry.TelemetryMixin, GalleryApiTestCase):
    """TEL-56: one count per finished image upload, by kind and outcome."""

    def setUp(self):
        super().setUp()
        testing_telemetry.clear()
        # The test client re-raises what the server would answer with a 500; the handler of the app is what runs here.
        self.client.raise_request_exception = False

    def uploads(self):
        return sorted((a['kind'], a['outcome'], value) for a, value in self.points('hairmatch.uploads'))

    def put_profile(self, upload):
        return self.client.put(reverse('profile_picture'), {'profile_picture': upload}, format='multipart')

    def test_a_stored_profile_picture_counts_profile_stored(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.put_profile(make_upload('a.png', fmt='PNG')).status_code, 200)
        self.assertEqual(self.uploads(), [('profile', 'stored', 1)])

    def test_a_profile_file_that_is_no_image_counts_invalid_image(self):
        self.assertEqual(self.put_profile(SimpleUploadedFile('a.png', NOT_AN_IMAGE, content_type='image/png')).status_code, 400)
        self.assertEqual(self.uploads(), [('profile', 'invalid_image', 1)])

    def test_a_profile_file_over_5_mb_counts_invalid_image(self):
        self.assertEqual(self.put_profile(SimpleUploadedFile('a.png', OVER_5_MB, content_type='image/png')).status_code, 400)
        self.assertEqual(self.uploads(), [('profile', 'invalid_image', 1)])

    def test_a_profile_save_that_breaks_counts_failed(self):
        with patch.object(User, 'save', side_effect=RuntimeError('db down')):
            self.assertEqual(self.put_profile(make_upload('a.png', fmt='PNG')).status_code, 500)
        self.assertEqual(self.uploads(), [('profile', 'failed', 1)])

    def test_a_profile_request_without_a_file_counts_nothing(self):
        self.assertEqual(self.client.put(reverse('profile_picture'), {}, format='multipart').status_code, 400)
        self.assertEqual(self.uploads(), [])

    def test_a_stored_gallery_photo_counts_gallery_stored(self):
        self.assertEqual(self._post(make_upload('a.png', fmt='PNG')).status_code, 201)
        self.assertEqual(self.uploads(), [('gallery', 'stored', 1)])

    def test_a_gallery_file_that_is_no_image_counts_invalid_image(self):
        self.assertEqual(self._post(SimpleUploadedFile('a.png', NOT_AN_IMAGE, content_type='image/png')).status_code, 400)
        self.assertEqual(self.uploads(), [('gallery', 'invalid_image', 1)])

    def test_a_gallery_file_over_5_mb_counts_invalid_image(self):
        self.assertEqual(self._post(SimpleUploadedFile('a.png', OVER_5_MB, content_type='image/png')).status_code, 400)
        self.assertEqual(self.uploads(), [('gallery', 'invalid_image', 1)])

    def test_a_gallery_save_that_breaks_counts_failed(self):
        with patch.object(GalleryPhoto, 'save', side_effect=RuntimeError('db down')):
            self.assertEqual(self._post(make_upload('a.png', fmt='PNG')).status_code, 500)
        self.assertEqual(self.uploads(), [('gallery', 'failed', 1)])

    def test_a_full_gallery_is_a_refusal_not_an_upload_result(self):
        self._fill(self.hairdresser, GALLERY_MAX_PHOTOS)
        self.assertEqual(self._post(make_upload('a.png', fmt='PNG')).status_code, 409)
        self.assertEqual(self.uploads(), [])
