# Create your tests here.
# hairmatch/ai_clients/tests/test_gemini_client.py
import io
import os
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError
from django.core.files.base import ContentFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.http import JsonResponse
from PIL import Image, ImageCms

from hairmatch.image_fixtures import make_image_bytes
from hairmatch.images import InvalidImage, to_webp, webp_name
from hairmatch.storage import S3MediaStorage

from users.models import Hairdresser, User
from preferences.models import Preferences
from hairmatch.ai_clients.gemini_client import (
    setup_environment,
    load_hairdresser_data,
    generate_ai_text,
    process_hairdresser_profile,
    hairdresser_profile_ai_completion
)

# It's good practice to place test files inside a 'tests' subdirectory 
# within the Django app, e.g., hairmatch/ai_clients/tests/test_gemini_client.py

class GeminiClientTest(TestCase):

    def setUp(self):
        """Set up test data for the tests."""
        self.user = User.objects.create(
            email="hairdresser@example.com",
            password="hairdresser123",
            first_name="Test",
            last_name="Hairdresser",
            phone="+5592984502222",
            complement="Apt 102",
            neighborhood="Downtown",
            city="Manaus",
            state="AM",
            address="Hairdresser Street",
            number="456",
            postal_code="69050750",
            role="hairdresser",
            rating=4.5
        )
        self.hairdresser = Hairdresser.objects.create(user=self.user, resume="Experienced with color.")
        self.preference = Preferences.objects.create(name='colorimetry')
        self.user.preferences.add(self.preference)

    @override_settings(GEMINI_API_KEY='test_key')
    @patch('hairmatch.ai_clients.gemini_client.genai.configure')
    def test_setup_environment_success(self, mock_configure):
        """Test that genai.configure is called when API key is present."""
        setup_environment()
        mock_configure.assert_called_once_with(api_key='test_key')

    @override_settings(GEMINI_API_KEY=None)
    def test_setup_environment_no_key_raises_error(self):
        """Test that a ValueError is raised if the API key is missing."""
        with self.assertRaisesMessage(ValueError, "GEMINI_API_KEY not defined"):
            setup_environment()

    def test_load_hairdresser_data_success(self):
        """Test loading an existing hairdresser's data."""
        data = load_hairdresser_data(self.hairdresser.id)
        self.assertIsNotNone(data)
        self.assertEqual(data['user']['id'], self.user.id)
        self.assertEqual(data['resume'], "Experienced with color.")

    def test_load_hairdresser_data_not_found(self):
        """Test loading a non-existent hairdresser returns None."""
        data = load_hairdresser_data(9999)
        self.assertIsNone(data)

    @patch('hairmatch.ai_clients.gemini_client.genai.GenerativeModel')
    def test_generate_ai_text(self, mock_generative_model):
        """Test the AI text generation function."""
        # Setup mock
        mock_model_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "This is a generated AI text."
        mock_model_instance.generate_content.return_value = mock_response
        mock_generative_model.return_value = mock_model_instance

        # Call function
        prompt = "Describe a hairdresser."
        result = generate_ai_text(prompt)

        # Assertions
        mock_generative_model.assert_called_with('gemini-2.0-flash')
        mock_model_instance.generate_content.assert_called_once()
        self.assertEqual(result, "This is a generated AI text.")

    @patch('hairmatch.ai_clients.gemini_client.generate_ai_text')
    def test_process_hairdresser_profile(self, mock_generate_ai_text):
        """Test the two-step profile processing logic."""
        # Setup mock to return different values on subsequent calls
        mock_generate_ai_text.side_effect = [
            "Relevant info: specializes in color.",
            "Final summary: This hairdresser is a color specialist."
        ]

        profile_data = {'name': 'Test', 'specialties': 'color'}
        result = process_hairdresser_profile(profile_data)

        # Assertions
        self.assertEqual(mock_generate_ai_text.call_count, 2)
        first_call_args = mock_generate_ai_text.call_args_list[0]
        self.assertIn(str(profile_data), first_call_args.args[0])

        second_call_args = mock_generate_ai_text.call_args_list[1]
        self.assertIn("Relevant info: specializes in color.", second_call_args.args[0])

        self.assertEqual(result, "Final summary: This hairdresser is a color specialist.")

    @patch('hairmatch.ai_clients.gemini_client.process_hairdresser_profile')
    @patch('hairmatch.ai_clients.gemini_client.setup_environment')
    def test_hairdresser_profile_ai_completion_success(self, mock_setup, mock_process):
        """Test the main completion view function on a successful run."""
        mock_process.return_value = "AI generated description."
        
        # This raw data mimics the structure before preference serialization
        hairdresser_data_raw = {
            'user': {'id': self.user.id},
            'resume': 'Experienced with color.',
            'preferences': [self.preference.id]
        }

        response = hairdresser_profile_ai_completion(hairdresser_data_raw)

        # Assertions
        mock_setup.assert_called_once()
        mock_process.assert_called_once()
        
        # Check that the preferences were correctly serialized for the prompt
        processed_data_arg = mock_process.call_args[0][0]
        self.assertEqual(processed_data_arg['preferences'][0]['name'], 'colorimetry')

        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 200)

    @patch('hairmatch.ai_clients.gemini_client.setup_environment', side_effect=ValueError("Test error"))
    def test_hairdresser_profile_ai_completion_config_error(self, mock_setup):
        """Test completion function when setup_environment fails."""
        response = hairdresser_profile_ai_completion({})
        self.assertEqual(response.status_code, 500)

    @patch('hairmatch.ai_clients.gemini_client.setup_environment')
    @patch('hairmatch.ai_clients.gemini_client.process_hairdresser_profile', side_effect=Exception("Unexpected"))
    def test_hairdresser_profile_ai_completion_unexpected_error(self, mock_process, mock_setup):
        """Test completion function with a generic unexpected error."""
        response = hairdresser_profile_ai_completion({'preferences': []})
        self.assertEqual(response.status_code, 500)


@override_settings(S3_BUCKET_NAME='test-bucket')
class S3MediaStorageTest(SimpleTestCase):

    def setUp(self):
        patcher = patch('hairmatch.storage.boto3.client')
        self.mock_client = patcher.start().return_value
        self.addCleanup(patcher.stop)
        self.storage = S3MediaStorage()

    @override_settings(S3_PUBLIC_ENDPOINT_URL='http://localhost:4566/')
    def test_url_uses_public_endpoint_path_style(self):
        self.assertEqual(
            self.storage.url('profile_pics/foto 1.jpg'),
            'http://localhost:4566/test-bucket/profile_pics/foto%201.jpg',
        )

    @override_settings(S3_PUBLIC_ENDPOINT_URL=None)
    def test_url_without_public_endpoint_uses_aws(self):
        self.mock_client.meta.region_name = 'us-east-2'
        self.assertEqual(
            self.storage.url('profile_pics/a.jpg'),
            'https://test-bucket.s3.us-east-2.amazonaws.com/profile_pics/a.jpg',
        )

    def test_exists_returns_false_on_404(self):
        self.mock_client.head_object.side_effect = ClientError(
            {'Error': {'Code': '404'}}, 'HeadObject'
        )
        self.assertFalse(self.storage.exists('missing.jpg'))

    def test_exists_reraises_other_errors(self):
        self.mock_client.head_object.side_effect = ClientError(
            {'Error': {'Code': '403'}}, 'HeadObject'
        )
        with self.assertRaises(ClientError):
            self.storage.exists('forbidden.jpg')

    def test_exists_returns_true_when_object_found(self):
        self.assertTrue(self.storage.exists('found.jpg'))
        self.mock_client.head_object.assert_called_once_with(Bucket='test-bucket', Key='found.jpg')

    def test_save_uploads_with_content_type(self):
        self.mock_client.head_object.side_effect = ClientError(
            {'Error': {'Code': '404'}}, 'HeadObject'
        )
        name = self.storage.save('profile_pics/a.png', ContentFile(b'data'))

        self.assertEqual(name, 'profile_pics/a.png')
        args, kwargs = self.mock_client.upload_fileobj.call_args
        self.assertEqual(args[1:], ('test-bucket', 'profile_pics/a.png'))
        self.assertEqual(kwargs['ExtraArgs'], {'ContentType': 'image/png'})

    def test_delete_removes_object(self):
        self.storage.delete('profile_pics/a.jpg')
        self.mock_client.delete_object.assert_called_once_with(
            Bucket='test-bucket', Key='profile_pics/a.jpg'
        )


def noise_image(size):
    """Incompressible RGB image, so encoded sizes react to encoder settings."""
    return Image.frombytes('RGB', size, os.urandom(size[0] * size[1] * 3))


class WebpNameTest(SimpleTestCase):

    def test_swaps_extension_and_lowercases_it(self):
        self.assertEqual(webp_name('dir/FOTO.JPG'), 'dir/FOTO.webp')

    def test_adds_extension_when_missing(self):
        self.assertEqual(webp_name('foto'), 'foto.webp')

    def test_only_replaces_the_last_extension(self):
        self.assertEqual(webp_name('a.b.png'), 'a.b.webp')


class ToWebpTest(SimpleTestCase):

    def convert(self, data):
        return Image.open(to_webp(ContentFile(data)))

    def test_jpeg_becomes_webp(self):
        result = self.convert(make_image_bytes(fmt='JPEG'))
        self.assertEqual(result.format, 'WEBP')
        self.assertEqual(result.size, (20, 10))

    def test_applies_exif_orientation_to_the_pixels(self):
        result = self.convert(make_image_bytes(size=(20, 10), orientation=6))
        self.assertEqual(result.size, (10, 20))

    def test_rotates_before_resizing(self):
        result = self.convert(make_image_bytes(size=(6000, 4000), orientation=6))
        self.assertEqual(result.size, (720, 1080))

    def test_limits_the_longest_side_to_1080_without_upscaling(self):
        cases = {
            (4000, 6000): (720, 1080),
            (6000, 4000): (1080, 720),
            (1080, 500): (1080, 500),
            (800, 600): (800, 600),
        }
        for size, expected in cases.items():
            with self.subTest(size=size):
                self.assertEqual(self.convert(make_image_bytes(size=size)).size, expected)

    def test_output_mode_keeps_alpha_only_when_the_source_has_it(self):
        cases = [
            ('RGBA', 'PNG', 'RGBA'),
            ('LA', 'PNG', 'RGBA'),
            ('P', 'PNG', 'RGBA'),
            ('CMYK', 'JPEG', 'RGB'),
            ('L', 'PNG', 'RGB'),
            ('RGB', 'JPEG', 'RGB'),
        ]
        for mode, fmt, expected in cases:
            with self.subTest(mode=mode, fmt=fmt):
                result = self.convert(make_image_bytes(mode=mode, fmt=fmt))
                self.assertEqual(result.mode, expected)

    def test_strips_exif_including_gps(self):
        source = make_image_bytes(orientation=6, gps=True)
        self.assertTrue(Image.open(io.BytesIO(source)).getexif())
        self.assertEqual(len(self.convert(source).getexif()), 0)

    def test_recodes_webp_input_and_strips_its_exif(self):
        source = make_image_bytes(fmt='WEBP', orientation=1, gps=True)
        self.assertTrue(Image.open(io.BytesIO(source)).getexif())
        result = self.convert(source)
        self.assertEqual(result.format, 'WEBP')
        self.assertEqual(len(result.getexif()), 0)

    def test_keeps_the_icc_profile(self):
        icc = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
        result = self.convert(make_image_bytes(icc_profile=icc))
        self.assertEqual(result.info['icc_profile'], icc)

    def test_drops_an_icc_profile_that_is_not_rgb(self):
        icc = bytearray(ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes())
        icc[16:20] = b'CMYK'
        result = self.convert(make_image_bytes(mode='CMYK', icc_profile=bytes(icc)))
        self.assertNotIn('icc_profile', result.info)

    def test_encodes_with_quality_80(self):
        noise = noise_image((200, 150))
        source = io.BytesIO()
        noise.save(source, 'PNG')
        reference = io.BytesIO()
        noise.save(reference, 'WEBP', quality=80, method=4)
        self.assertEqual(
            len(to_webp(ContentFile(source.getvalue())).read()), len(reference.getvalue())
        )

    def test_animated_input_keeps_only_the_first_frame(self):
        for fmt in ('GIF', 'WEBP'):
            with self.subTest(fmt=fmt):
                source = make_image_bytes(fmt=fmt, frames=3)
                self.assertEqual(Image.open(io.BytesIO(source)).n_frames, 3)
                result = self.convert(source)
                self.assertEqual(result.format, 'WEBP')
                self.assertEqual(getattr(result, 'n_frames', 1), 1)

    def test_rejects_files_that_are_not_decodable_images(self):
        noisy_jpeg = io.BytesIO()
        noise_image((300, 300)).save(noisy_jpeg, 'JPEG')
        cases = {
            'garbage': b'file_content',
            'text with image name': b'just some notes\n' * 20,
            'truncated jpeg': noisy_jpeg.getvalue()[: len(noisy_jpeg.getvalue()) // 2],
        }
        for label, data in cases.items():
            with self.subTest(case=label):
                with self.assertRaises(InvalidImage):
                    to_webp(ContentFile(data))

    def test_rejects_images_over_the_pixel_limit(self):
        with patch.object(Image, 'MAX_IMAGE_PIXELS', 10):
            with self.assertRaises(InvalidImage):
                to_webp(ContentFile(make_image_bytes(size=(20, 10))))
