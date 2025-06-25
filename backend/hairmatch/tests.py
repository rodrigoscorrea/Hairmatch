# Create your tests here.
# hairmatch/ai_clients/tests/test_gemini_client.py
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.http import JsonResponse

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

